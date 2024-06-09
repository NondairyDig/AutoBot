from fastapi import APIRouter, HTTPException
from ..src.Host import Host
from .nifi import statistics as nifi_stats
from ..config import ASYNC_CELERY_TASKS, ADMIN_CREDENTIALS
from ..src.ServiceNow import create_incident, Incident
from ..src.Archive import ArchiveIncident

router = APIRouter(tags=["Statistics"], prefix="/stats")
router.include_router(nifi_stats.router)


@router.get("/host")
async def stats(hostname: str):
	host = Host(hostname=hostname)
	host._connect(ADMIN_CREDENTIALS["username"], ADMIN_CREDENTIALS["password"])
	return {
		"cpu": host.get_cpu_usage(),
		"mem": host.get_memory_usage(),
		"root": host.get_root_usage(),
		"disks": host.get_all_disks_usage(),
		"io": host.get_io()
	}


@router.get("/flags")
async def get_flags():
	return list(await ASYNC_CELERY_TASKS.find({}, {"_id": 0}).to_list(length=None))


@router.get("/flag")
async def get_flag(flag: str):
	return await ASYNC_CELERY_TASKS.find_one({"name": flag}, {"_id": 0})


@router.post("/flag")
async def set_flag(flag: str, value: str):
	await ASYNC_CELERY_TASKS.update_one({"name": flag}, {"$set": {"value": value}})
	return {"flag": flag, "value": value}


@router.delete("/flag")
async def delete_flag(flag: str):
	await ASYNC_CELERY_TASKS.delete_one({"name": flag})
	return {"deleted": flag}