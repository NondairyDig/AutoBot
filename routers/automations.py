from fastapi import APIRouter, Request, WebSocket
from ..src.Alert import Alert
from ..utils.task_manager import task_manager
from typing import Dict, Any


router = APIRouter(prefix="/automations", tags=["Automations"])


@router.get("/automation_arguments")
async def get_task_arguments(task_name: str):
	return await task_manager.get_args(task_name)


@router.get("/list")
async def get_tasks():
	return await task_manager.list_automations()


@router.post("/schedule")
async def schedule_automation(task_name: str, task_args: Dict[str, Any]):
	task = await task_manager.schedule_task(task_name, **task_args)
	return f"Task {task_name} scheduled with ID: {task.id}"


@router.post("/run")
async def run_automation(task_name: str, task_args: Dict[str, Any]):
	return await task_manager.run_task(task_name, **task_args)


@router.get("/fix")
async def auto_fix(request: Request):
	alert = Alert()
	await alert.parse(request.query_params)
	return await alert.automation_picker()


@router.get("/status")
async def get_auto_status(automation_id: str):
	return await task_manager.get_task_status(automation_id)


@router.websocket("/track")
async def track_automation(websocket: WebSocket, task_id):
	await websocket.accept()
	return await task_manager.live_track_task(websocket, task_id)