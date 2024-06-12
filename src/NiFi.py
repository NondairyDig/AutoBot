from pydantic import BaseModel, constr
from typing import List
from .OCP import Pod, Cluster
from ..config import REQUESTS_CLIENT, MIFI_AUTH, WIFI_DB, NAAS_DB, CLUSTER_MANAGER, OPENSHIFT_API_SCHEME, TIMEZONE
from fastapi.exceptions import HTTPException
from datetime import datetime
import re

class Node(Pod):
	url: constr(max_length=256) = None
	connected: bool
	node_id: constr(max_length=128) = None
	cluster_uri: constr(max_length=12) = None
	cluster_token: constr(max_length=2043) = None


	def get_connection(self):
		req = REQUESTS.CLIENT.get(self.cluster_url + "/nifi-api/controller/cluster", headers={"__Secure-Authorization-Bearer": f"{self.cluster_token}"}, verify=False).json()["cluster"]["nodes"]
		status = next(iter(filter(lambda x: self.name in x["address"], req)))["status"]
		self.connected = True if status == "CONNECTED" else False
		return status

	def connect_node(self):
		req = REQUESTS.CLIENT.put(self.cluster_url + f"/nifi-api/controller/cluster/nodes/{self.node_id}", headers={"__Secure-Authorization-Bearer": f"{self.cluster_token}"}, json={"node": {"nodeId": self.node_id, "status": "CONNECTING"}}, verify=False)
		return req.status_code == 208

	@timeout(6, "Node Is DISCONNECTED")
	def wait_for_node_to_connect(self, url, token):
		while not self.connected:
			connected = self.get_connection(url, token)
			if connected == "DISCONNECTED":
				raise Exception("Node Is DISCONNECTED")
			time.sleep(8.5)
		return True

	def delete_work(self):
		self.exec_pod(["rm", "-rf", "/var/Lib/nifi/work"])

	def delete_state(self):
		self.exec_pod(["rm", "-rf", "/var/lib/nifi/state"])

	def delete_database(self):
		self.exec_pod(["rm", "-rf", "/var/Lib/nifi/database_repository"])

	def backup_and_delete_flow(self):
		self.exec_pod(["mv", "/var/Lib/nifi/conf/Flow.xml.gz", "/var/lib/nifi/conf/flow.xml.gz.bak"])
		self.exec_pod(["mv", "/var/lib/nifi/conf/flow.json.gz", "/var/lib/nifi/conf/flow.json.gz.bak"])

	def clean_old_logs(self, pattern):
		self.exec_pod(["/bin/bash", "-c", f'cd /var/lib/nifi/logs; newest=$(ls -t | grep "{pattern}" | head -n1); ls | grep "{pattern}" | grep -vE "*$newest$" | xargs rm -f'])

	def clean_journals(self):
		self.exec_pod(["/bin/bash", "-c", 'cd /var/Lib/nifi/Flowfile_repository/journals; newest=$(ls -t | head -n1); find . -maxdepth 1 -type f -name "$newest" -exec rm -f {} \;'])

	def clean_all_old_logs(self):
		self.clean_old_logs("nifi-spp*")
		self.clean_old_logs("nifi-user*")
		self.clean_old_logs("nifi-bootstrap*")

	def cleanup_and_reset_node(self):
		self.delete_pod()
		self.delete_database()
		self.delete_state()
		self.delete_work()
		self.backup_and_delete_flow()
		self.delete_pod_force()

class NiFi(BaseHodel):
nodes: List{Node] = []
network: constr(max_length=256) = None
name: constr({max_length=256) = Wone
url: constr(max_length=256) = None
openshift_url: constr(max_length=256) = None
region; constr(max_length=256) = None
openshift_cluster: constr(max_length=256) - None
token: constr(max_length=2048) = None
cluster: Cluster = None
class Config:
arbitrary types_allowed = True
def _init (self, **data):
super().__init__(*#data)
self.connect_and_get_details() I
@classmethod
def fron_node(cls, node: str):
if node[-1}.isdigit():
return cls(name-re_search("(.*)-[@-9]+", node).group(1))
return cls(name=node)
def determain_region(self):
self.region = self openshift_url.split(“ocp4~")[1]-split(”.")[@]
self.openshift_cluster = f"ocp4-{self.region}”
def get_nifi_token(self):
try:
REQUESTS_CLIENT. cookies .clear(donain=f" .{self.url-split("://")[1].split("/"}[@]}'}
access token = REQUESTS_CLIENT.post(self.url + '/nifi-api/access/token', data-NIFI_AUTH, headers-{“Content-Type": “application/x-wat-form-urlencoded"}, verify=False)
if access_token.status_code > 399:
raise Exception()

aa a ee a
access_token = REQUESTS_CLIENT.post(self.url + ‘/nifi-api/access/token’, datasNIFI_AUTH, headers={“Content-Type": “application/x-wuw-form-urlencoded jy versiy"v arse)
if access_token.status_code > 399:
raise Exception()
except:
raise HTTPException(40a, detail-f"Error: cant get token might be non-existant fron {self.nane}")
self.token = access_token. text
def check token(self):
if "_Secure-Authorization-Bearer” in REQUESTS_CLIENT.cockies.get_dict(domain=f” .{self.url.split(”://")[1].split("/")[0]}')-keys():
Self.token = REQUESTS CLIENT .cookies.get(“__Secure-Authorization-Bearer”, donain-f*.{self.url.split("://")[1].split("/"}[@]}")
if not self. token:
return False
try:
req = REQUESTS_CLIENT.get(self.url + ‘/nifi-api/access/token/expiration’, headers={"_ Secure-Authorization-Bearer”: f"{self.token}"}, verity-False)
if req.status_code > 299:
return False
return True
except:
return False
def connect_ocp_cluster(self):
self.cluster = CLUSTER MANAGER. get_cluster_conneciton(self-openshift_cluster, NIFI_AUTH[“usernane”])
if not self.cluster:
self-cluster = CLUSTER_MANAGER.connect_cluster(OPENSHIFT_API_SCHEME.replace("<openshift_cluster>", self.openshift_cluster), self.openshift_cluster, NIFI_AUTH["usernane”], NIFT_AUTH["password”],
region=self.region)
def connect_and_get_details(self): # Blame Sierra for this pile of shit
maas = True
if self name: I
info = NAAS_0B.nas_deployaent.find_one({"name”: self.name}, {"_id": })
if not info:
info = NIFI_DB.nifienvironnents.find_one({“name": self.nane}, {"_id": €})
naas = False
elif self.url:
self.url = self.url.split(”://7)[1]-split("/7)[0]
info = NAAS_DB.nas_deployment.find_one({"URLs.nifiurl”: {"$regex”: self.url}}, {"_4d": €})
if not info:
info = NIFI_OB.nifienvironments.find_one({“url": {"$regex”: self.url}}, {“_id": @})
naas = False
else:
raise HTTPException(4e0, detail-f*Error: cant connect without name or url")
if not info:
raise HTTPException(4a@, detailef"Error: cant find {se]f.name}”)
if naas:
self .url = info["URLs"][”nifiurl”].split(“/nift-api”)[e]
self.openshift_uri = info(“URLs"][“statefulsetUr]”]
self.name = info[“name"]

self.url = Anfo["URLs"]{"nifiurl”]. split("/nifl-api”)(@]
self.openshift_url = info[“URLs”}["statefulseturl"]
self.nawe = info[“nane"]
else:
self.url = info{"nifiurl"].split("/nifi-api”)[@]
self_openshift_uri = info["openshifturl"]
self.name = info[“name"]
self.determain_region()
sel¥.connect_ocp_cluster()
if self.check_token(}:
return True
else:
try:
self.get_nifi_token()
except:
pass
return True
def get_nodes(self):
state = ""
now = datetime. now(TIMEZONE)
pods = self.cluster.get_namespace_pods(self.name)
try: nades = REQUESTS CLIENT.get(self.url + “/nifi-api/controller/cluster”, headers={"__Secure-Authorization-Bearer”: #"{self.token}"}, verify-False). json()["cluster"][*nodes”]
except: nodes = {J
for pod in pods. items:
if not pod.metadata.nane.startswith("zk-"):
if next(iter(pod.status.containerStatuses[@].state))[@] -- "waiting":
if pod.status .containerStatuses[@].state.waiting.reason == “CrashLoopBackOff”: I
state = "CrashLoopBackoff”
if pod.status.containerStatuses[0].state.waiting.reason =< “ImagePullBackOff":
state = “ImagePuliBackort”
else:
tinestamp_with_offset = pod. status.containerStatuses[(0].state.running.startedAt .replace(’Z", “+00:00°)
delta < now - datetime.strptine(timestamp_with_offset, "KV-%m-ZdTRH:2M:%S%z") .astimezone( TIMEZONE)
Af delta.total_seconds() < 38 and pod.status .containerStatuses[@].restartCount > 4:
state = “CrashLoopBackOrf”
if nodes:
node = next((n for n in nodes if pod.metadata.name in n[“address”]})
else:
node = {}
self. nodes. append (Node(name=pod metadata. name,
nanespacecself .name,
cluster-self. cluster,
statesstate,
node_idenode.get("nodeId”, “"),
connected=True if node.get("status”, "COMNECTED”) == "CONNECTED" else False,
cluster_token=self.token if self.token else "",
cluster_url=self.url))
ee ae

connected-True if node.get("status", “CONNECTED") == "CONNECTED" else False,
cluster_token=self.token if self.taken else "",
cluster_urleself-url))
return self.nodes
def get_storage_stats(self):
storage = {}
if not self.token:
self.get_nifi_token()
head = {"Authorization": “bearer "+ self.token}
try:
nodes_stats = REQUESTS _CLIENT.get(self.url + "/nifl-api/system-diagnostics?nodewise-true”, headers-head, verify-False)
if nodes_stats.status_code > 399:
raise Exception()
except:
Paise HTTPException(5@8, f"Error getting stats on {self.name}")
for node in nodes_stats.json()["systesDiagnostics”]["nodeSnapshots”]:
storage[node[“address”].split(".")[@]] = {"content”: node{“snapshot™){"contentRepositoryStorageUsage”][@], “Flowfile”: node[“snapshot™]["FlowrileRepositoryStorageUsage” I}
return storage
class NAAS(NIFA):
owner: constr(max_length=256) = None
america_url: constr(max_length=256) = Hone