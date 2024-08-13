from fastapi import APIRouter
from ..src.ServiceNOW import create_incident, Incident, get_incident
from ..src.Archive import Archive
from ..src.Alert import AlertScanner

router = APIRouter(prefix="/general", tags=["Etc"])

@router.get("/get_incident")
async def get_incident_endpoint(incident_number: str):
	return get_incident(incident_number)

@router.post("/create_incident")
async def create_incident_endpoint(incident: Incident):
	return create_incident(incident)

@router.get("/search_responsible_group")
async def search_group_by_object(search: str):
	return await Archive.get_responsible_team(await Archive.search(search, "TEAM", True))