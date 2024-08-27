import asyncio
import inspect
import logging
from fastapi import HTTPException, WebSocket
from celery import Celery
from celery.result import AsyncResult
from functools import wraps
from celery.utils.log import get_task_logger
from copy import copy
from typing import Any, Dict


class AutomationManager(Celery):
    task_registry: Dict[str, Any] = {}

    async def list_tasks(self) -> Dict[str, Any]:
        tasks = copy(self.tasks)
        for task_name in list(tasks):
            if "celery." in task_name:
                tasks.pop(task_name, None)
        return tasks

    async def list_automations(self) -> Dict[str, Dict[str, Any]]:
        automations = {}
        for task_name, task_obj in self.tasks.items():
            if "celery." in task_name:
                continue
            automations[task_name] = {
                "description": self.task_registry[task_name]["description"],
                "arguments": {k: str(v) for k, v in self.task_registry[task_name]["arguments"].items()}
            }
        return automations

    async def list_task_names(self) -> list:
        return [task_name for task_name in self.tasks.keys() if "celery." not in task_name]

    async def get_task(self, task_name: str) -> Any:
        return self.tasks[task_name]

    async def get_args(self, task_name: str) -> Dict[str, str]:
        args = self.task_registry[task_name]["arguments"].items()
        return {k: str(v) for k, v in args}

    async def run_task(self, task_name: str, **kwargs) -> Any:
        await self.check_args(task_name, kwargs)
        res = await asyncio.to_thread(self.send_task, task_name, args=[False], kwargs=kwargs)
        return await asyncio.to_thread(res.get)

    async def schedule_task(self, task_name: str, **kwargs) -> Any:
        await self.check_args(task_name, kwargs)
        return await asyncio.to_thread(self.send_task, task_name, args=[False], kwargs=kwargs)
    
    async def schedule_alert(self, automation_name, archive, **kwargs):
        await self.check_args(automation_name, kwargs)
        auto = await asyncio.to_thread(self.send_task, automation_name, args=[dict(archive) if archive else False], kwargs=kwargs)
        return auto.id


    async def check_args(self, task_name: str, args: dict) -> None:
        # Check if the task exists
        if task_name not in self.task_registry:
            raise HTTPException(status_code=404, detail="Task not found")
        
        # Check if the arguments are of the right type and no garbage args
        for arg_name, arg_value in args.items():
            expected_type = self.task_registry[task_name]["arguments"].get(arg_name, Exception)
            if expected_type is Exception:
                raise HTTPException(status_code=400, detail=f"Got unexpected argument {arg_name}")
            if expected_type is not None and not isinstance(arg_value, expected_type):
                raise HTTPException(status_code=400, detail=f"Invalid type for argument {arg_name}")

    async def track_task(self, websocket: WebSocket, task_id: str) -> None:
        res = AsyncResult(task_id)
        while not await asyncio.to_thread(res.ready):
            await asyncio.sleep(0.1)
            await websocket.send_json({"id": task_id, "state": res.state, "progress": res.info})
        return await asyncio.to_thread(res.get)

    async def get_task_status(self, task_id: str) -> Any:
        res = AsyncResult(task_id)
        while not await asyncio.to_thread(res.ready):
            await asyncio.sleep(0.1)
        return await asyncio.to_thread(res.get)


task_manager = AutomationManager('task_manager')
task_manager.conf.update(
    broker_url=f"redis://redis-autobot:6379/0",
    task_track_started=True,
    broker_connection_retry_on_startup=True
)


def automation(total_steps: int = 1, description: str = "Automation", AutoFix: Any = False):
    def decorator(func):
        @task_manager.task(bind=True, name=func.__name__, tags=[func.__module__])
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            logger = get_task_logger(self.name)
            logger.setLevel(logging.INFO)
            logger.propagate = False
            
            logger.info(f"Task {self.name} has Started", extra={"id": self.request.id, "automation_name": self.name, "progress": "0.00%", "state": "STARTED", "parameters": kwargs})

            def update_progress(current, output=""):
                self.update_state(state="PROGRESS", meta=output)
                logger.info(output, extra={"id": self.request.id, "automation_name": self.name, "progress": f"{float(current)/float(total_steps)*100:.2f}%" if isinstance(type(total_steps), (float, int)) else f"?%", "state": "PROGRESS"})
            
            self.update_progress = update_progress

            sig = inspect.signature(func)
            defaults = {name: param.default for name, param in sig.parameters.items() if param.default is not inspect.Parameter.empty}
            for name, default_value in defaults.items():
                if name not in kwargs:
                    kwargs[name] = default_value
            try:
                res = func(self, **kwargs)
            except Exception as e:
                logger.error(f"Task {self.name} has Failed: {str(e)}", extra={"id": self.request.id, "automation_name": self.name, "progress": "100.0%", "state": "FAILED", "parameters": kwargs})
                raise e
            logger.info(f"Task {self.name} has Completed", extra={"id": self.request.id, "automation_name": self.name, "progress": "100.0%", "state": "SUCCESS", "parameters": kwargs})
            return res
        sig = inspect.signature(func)
        task_manager.task_registry[func.__name__] = {"arguments": {name: param.annotation if param.annotation is not inspect.Parameter.empty else None for name, param in sig.parameters.items()}, "description": description, "autofix": AutoFix}
        task_manager.task_registry[func.__name__]["arguments"].pop("self", None)
        return wrapper
    return decorator