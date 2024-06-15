from pydantic import BaseModel, constr
from fastapi import WebSocket
from typing import List
from openshift.dynamic import DynamicClient
from openshift.helper.userpassauth import OCPLoginConfiguration
from kubernetes import client
from kubernetes.client.exceptions import ApiException
from kubernetes.stream import stream
from ..utils.general import timeout
import time
import asyncio


class Cluster(DynamicClient):
	name: constr(max_length=256) = None
	region: constr(max_length=256) = None
	token_expires: int = 0

	def check_token(self):
		if time.time() > self.token_expires:
			return False
		return True

	def get_namespace_pods(self, namespace: str):
		return self.resources.get(api_version="v1", kind="Pod").get(namespace=namespace)


class ClusterManager(BaseModel):
	clusters: List[Cluster] = []


class Config:
	arbitrary_types_allowed = True


	def get_cluster_connection(self, cluster_name: str, username: str = None) -> Cluster:
		for cluster in self.clusters:
			if cluster.name == cluster_name:
				if username:
					if cluster.configuration.ocp_username != username:
						continue
				if cluster.check_token():
					return cluster
				else:
					self.clusters.remove(cluster)
		return None

	def connect_cluster(self, api_url: str, cluster_name: str = None, username: str = None, password: str = None, token=None, region="") -> Cluster:
		if not username and not password:
			if token:
				config = OCPLoginConfiguration(api_url, api_key={"authorization": "Bearer " + token})
			else:
				raise Exception("Username and password or token is required")
		else:
			config = OCPLoginConfiguration(api_url, ocp_username=username, ocp_password=password)
		config.verify_ssl = False
		if not token:
			config.get_token()
		api_cli = client.ApiClient(configuration=config)
		cluster = Cluster(api_cli)
		cluster.token_expires = cluster.configuration.token["expires_in"] + time.time()
		cluster.name = cluster_name
		cluster.region = region
		self.clusters.append(cluster)
		return cluster


class Pod(BaseModel):
	name: constr(max_length=256) = None
	cluster: Cluster = None
	namespace: constr(max_length=256) = None
	state: constr(max_length=256) = None


class Config:
	arbitrary_types_allowed = True

	@timeout(6, "Pod timed out deletion")
	def wait_for_pod_deletion(self):
		pod = self.cluster.resources.get(api_version="v1", kind="Pod").get(namespace=self.namespace, name=self.name)
		while pod.status.phase != "Pending":
			try:
				pod = self.cluster.resources.get(api_version="v1", kind="Pod").get(namespace=self.namespace, name=self.name)
			except ApiException:
				pass
			time.sleep(0.5)
		return True

	@timeout(63, "Pod timed out initializing")
	def wait_for_pod_running(self):
		pod = self.cluster.resources.get(api_version="v1", kind="Pod").get(namespace=self.namespace, name=self.name)
		while pod.status.phase != "Running":
			try:
				pod = self.cluster.resources.get(api_version="v1", kind="Pod").get(namespace=self.namespace, name=self.name)
			except ApiException:
				pass
			time.sleep(0.5)
		return True

	def exec_pod(self, command: list):
		api = client.CoreV1Api(self.cluster.client)
		return stream(api.connect_get_namespaced_pod_exec, self.name, self.namespace, command=command, stdin=False, stdout=True, stderr=True, tty=False)

	def delete_pod(self):
		pod = self.cluster.resources.get(api_version="v1", kind="Pod")
		pod.delete(namespace=self.namespace, name=self.name)
		self.wait_for_pod_deletion()
		self.wait_for_pod_running()
		return True

	def delete_pod_force(self):
		pod = self.cluster.resources.get(api_version="v1", kind="Pod")
		pod.delete(namespace=self.namespace, name=self.name, grace_period_seconds=0)
		return True

	def delete_pod_no_wait(self):
		pod = self.cluster.resources.get(api_version="v1", kind="Pod")
		pod.delete(namespace=self.namespace, name=self.name)
		return True

	async def stream_logs(self, websocket: WebSocket):
		api = client.CoreV1Api(self.cluster.client)
		log_stream = stream(api.connect_get_namespaced_pod_exec, self.name, self.namespace, command=["/bin/bash", "-c", "STAIL_LOGS"],
							stdout=True, stderr=True, stdin=False, tty=False, _preload_content=False)
		try:
			while log_stream.is_open():
				log_stream.update(timeout=1)
				if log_stream.peek_stdout():
					await websocket.send_text(log_stream.read_stdout())
				if log_stream.peek_stderr():
					await websocket.send_text(log_stream.read_stderr())
				await asyncio.sleep(0.1)
		except Exception as e:
			return
		finally:
			await websocket.close()