import json
from fastapi.exceptions import HTTPException
from fastapi import status
from .Host import Host
from .Zookeeper import Zookeeper
from typing import List
from ..config import VICTORIA_QUERY_METRICS_URL, REQUESTS_CLIENT, KAFKA_AUTH, REASSIGN_COMMAND
from pydantic import BaseModel, constr

class Broker(Host):
	id: constr(max_length=256) = None
	cluster: constr(max_length=256) = None
	listen_port: constr(max_length=5) = "9092"
	up: bool = True
	connected_to_cluster: bool = True

	def __init__(self, **data):
		super().__init__(**data)
		self.get_broker_state()

	def connect_to_broker(self):
		self._connect(KAFKA_AUTH["username"], KAFKA_AUTH["password"])
		return True

	def get_broker_state(self):
		stat = REQUESTS_CLIENT.get(VICTORIA_QUERY_METRICS_URL + f'kafka_broker_info{{address="{self.hostname}:{self.listen_port}"}}').json()["data"]["result"]
		if not stat:
			raise HTTPException(status.HTTP_400_BAD_REQUEST, "Broker Doesn't exist")
		try:
			self.connect_to_broker()
		except:
			self.up = False
		try:
			self.connected_to_cluster = bool(stat[0]["value"])
		except:
			self.connected_to_cluster = False
		if self.connection:
			try:
				if len(self._execute("ps -ef | grep java.*kafka | grep -v grep")) > 10:
					self.up = True
				else:
					self.up = False
			except:
				self.up = False

	def stop(self):
		self._connect_and_execute_no_output("pkill -9 .*java.*kafka.*")
		return True

	def start(self):
		if self.up:
			raise HTTPException(status.HTTP_208_ALREADY_REPORTED, "Broker is already up")
		else:
			if self.connect_to_broker():
				return self._execute("/home/kafka/scripts/daemon-kafka-start")

class KafkaCluster(BaseModel):
	name: constr(max_length=256) = None
	brokers: List[Broker] = []
	zookeepers: List[Zookeeper] = []
	region: constr(max_length=256) = None
	network: constr(max_length=256) = None

	def __init__(self, **data):
		super().__init__(**data)
		self.get_brokers()
		self.get_zookeepers()

	"""
	an example if ever going full async
	"""
	@classmethod
	async def create(cls, **data):
		self = cls(**data)
		await asyncio.gather(self.get_brokers(), self.get_zookeepers())
		return self

	def get_brokers(self):
		info = REQUESTS_CLIENT.get(VICTORIA_QUERY_METRICS_URL + f'kafka_broker_info{{cluster="{self.name}"}}').json()
		for broker in info["data"]["result"]:
			self.brokers.append(Broker(hostname=broker["metric"]["address"].split(":")[0], region=broker["metric"]["site"],
									   listen_port=broker["metric"]["address"].split(":")[1], state=broker["value"][1]))
		return True

	def get_zookeepers(self):
		info = REQUESTS_CLIENT.get(VICTORIA_QUERY_METRICS_URL + f'up{{job="zookeeper", cluster="{self.name}"}}').json()
		zookeeper_list = ""
		for zook in info["data"]["result"]:
			self.zookeepers.append(Zookeeper(hostname=zook["metric"]["instance"].split(":")[0], region=zook["metric"]["site"]))
			zookeeper_list += f"{self.zookeepers[-1].hostname}:{self.zookeepers[-1].listen_port},"
		zookeeper_list = zookeeper_list.removesuffix(",")
		return zookeeper_list

	def connect_to_random_broker(self) -> Broker:
		for broker in self.brokers:
			try:
				broker._connect(KAFKA_AUTH["username"], KAFKA_AUTH["password"])
				return broker
			except:
				pass
		else:
			raise HTTPException(status.HTTP_417_EXPECTATION_FAILED, "Couldn't connect to any broker")

	def partition_reassignment(self, topic: str, partitions: list):
		broker = self.connect_to_random_broker()
		if partitions == ["*"]:
			topic_to_move = {"topics": [{"topic": topic}], "version": 1}
		else:
			topic_to_move = {"topics": [{"topic": topic, "partitions": [{"partition": int(p)} for p in partitions]}], "version": 1}
		broker._execute(f'echo \'{json.dumps(topic_to_move)}\' > hurricane.json')
		command = REASSIGN_COMMAND.replace("<zook>", self.get_zookeepers()).removeprefix(",")
		proposed = broker._execute(command + f' --broker-list {",".join(str(i) for i in range(1, len(self.brokers) + 1))}' + ' --topics-to-move-json-file hurricane.json --generate').split("Proposed partition reassignment configuration")[4]
		broker._execute(f'echo \'{proposed}\' > hurricane_generated.json')
		broker._execute(f'export KAFKA_OPTS="-Djava.security.auth.login.config=/home/kafka/config/client_jaas.conf" && {command} --reassignment-json-file hurricane_generated.json --execute')
		return broker._execute(f'{command} --reassignment-json-file hurricane_generated.json --verify')