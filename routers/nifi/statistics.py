from fastapi import APIRouter, WebSocket
from ...src.Nifi import NiFi

router = APIRouter(tags=["Statistics"], prefix="/nifi7")

@router.get("/")
async def nifi_get_nodes(cluster_name: str):
	clust = NiFi(name=cluster_name)
	return [node.name for node in clust.get_nodes()]

@router.websocket("/stream_logs")
async def stream_logs(websocket: WebSocket, node: str):
	await websocket.accept()
	clust = NiFi.from_node(node)
	clust.get_nodes()
	for pod in clust.nodes:
		if pod.name == node:
			await pod.stream_logs(websocket)