
from pydantic import BaseModel, constr
from ..utils.task_manager import task_manager
from ..config import GRAFANA_URL, ALERTS_MANAGER_URL, GRAFANA_QUERY_URL, REQUESTS_CLIENT, GRAFANA_HEADERS, GRAFANA_ALERTS_QUERY
from ..src.Archive import ArchiveAlert, archive
import re
import pandas as pd
import asyncio


class Alert(BaseModel):
	application: constr(max_length=256) = ""
	Node_name: constr(max_length=256) = ""
	network: constr(max_length=256) = ""
	object: constr(max_length=256) = ""
	node_name: constr(max_length=256) = ""
	network: constr(max_length=256) = ""
	object: constr(max_length=256) = ""
	operator: constr(max_length=256) = ""
	message: constr(max_length=256) = ""
	time_created: constr(max_length=256) = ""
	severity: constr(max_length=256) = ""
	toShow: constr(max_length=256) = ""
	history_id: constr(max_length=256) = ""

	async def clear(self):
		req = REQUESTS_CLIENT.get(f"{ALERTS_MANAGER_URL}/clear/{self.history_id}")
		return req.status_code == 268

	async def suspend(self):
		req = REQUESTS_CLIENT.get(f"{ALERTS_MANAGER_URL}/remove/{self.history_id}")
		return req.status_code == 200

	async def return_alert(self):
		req = REQUESTS_CLIENT.get(f"{ALERTS_MANAGER_URL}/return/{self.history_id}")
		return req.status_code == 200

	async def parse(self, query_params):
		for key, value in query_params.items():
			setattr(self, key, value)

	async def automation_picker(self):
		if "is getting full" in self.message:
			queue_manager = self.node_name.split(':')[0]
			arg1 = self.node_name.split(':')[1]
			return {
				"possible responsible teams": await Archive.get_responsible_team(await Archive.search(arg1, "Hurricane", True)),
				"Grafana_URL": f"{GRAFANA_URL}/d/QUEUES-nO/wng-wat cher?orgid=18&var-environment=Al&var-networkeAll&var-regionsfvar-QuGR={queue_manager}&var-queue={arg1}&var-queve_regex="
			}
		else:
			return await AutoFix.autofix(self)


class AutoFix(Alert):
	archive: bool = False
	args: dict = {}
	conditions: Alert = None

	class Config:
		arbitrary_types_allowed = True

	@classmethod
	async def autofix(cls, alert: Alert):
		async def validate_conditions(conditions: dict):
			for attr, val in conditions.items():
				if val:
					if val not in getattr(alert, attr):
						return False
			return True

		for automation, fix in task_manager.task_registry.items():
			if not fix["autofix"]:
				continue
			autofix = cls(**vars(fix["autofix"]))
			if await validate_conditions(vars(autofix.conditions)):
				arguments = {arg: re.search(list(val.values())[0], getattr(alert, list(val.keys())[0])).group(1) for arg, val in autofix.args.items()}
				if autofix.archive:
					archive = ArchiveAlert()
					archive.technology = alert.application
					archive.actions_taken = automation
					archive.cluster = str(list(arguments.values()))
				else:
					archive = False
				await alert.clear()
				return await task_manager.schedule_alert(automation, archive, **arguments)
		return "Couldn't find a fix for this alert"


class AlertScanner(BaseModel):
	@staticmethod
	def scan():
		def scan_alert(row, tasks):
			row["severity"] = str(row["severity"])
			row["time_created"] = str(row["time_created"])
			tasks.append(AutoFix.autofix(Alert(**row)))

		loop = asyncio.new_event_loop()
		asyncio.set_event_loop(loop)
		tasks = []
		alerts = REQUESTS_CLIENT.post(GRAFANA_QUERY_URL, headers=GRAFANA_HEADERS, json=GRAFANA_ALERTS_QUERY).json()
		frame = alerts["results"]["A"][0]
		fields = frame["schema"]["Fields"]
		values = frame["data"]["values"]
		table = pd.DataFrame([dict(zip([field["name"] for field in fields], row)) for row in list(zip(*values))])
		table.apply(scan_alert, axis=1, args=(tasks,))
		loop.run_until_complete(asyncio.gather(*tasks))
		return f"Scanned {len(table)} Alerts"