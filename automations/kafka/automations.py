from ...src.Kafka import KafkaCluster, Broker
from ...src.Alert import AutoFix, Alert
from typing import List
from ...utils.task_manager import automation
from fastapi.exceptions import HTTPException
from fastapi import status


@automation(total_steps=2, description="Reassign Partitions on a Kafka Cluster, with select partitions", AutoFix=False)
def partition_reassignment(self, cluster: str, topic: str, partitions: List[int|str] = ["*"]):
	# for all partitions pass "*", for specific partitions pass partitions as a list
	self.update_progress(1, "Connecting to Cluster")
	current = KafkaCluster(name=cluster)
	self.update_progress(2, "Reassigning Partitions")
	return current.partition_reassignment(topic, partitions).split("\n")


@automation(total_steps=3, description="Reset Filebeat on A Kafka Broker", AutoFix=AutoFix(archive=True, conditions=Alert(application="kafka", message="/mnt/logs"), args={"host": r"(.*):.*"}))
def reset_filebeat(self, host: str):
	broker = Broker(hostname=host)
	self.update_progress(1, "Connecting to Broker")
	broker.connect_to_broker()
	self.update_progress(2, "Resetting Filebeat")
	broker.execute("pkill -9 .*filebeat.*7")
	self.update_progress(3, "Getting Storage Stats")
	broker.connect_to_broker()
	return {"Reseted Filebeat, Current Usage:": broker.get_all_disks_usage()}


@automation(total_steps=2, description="Check Kafka Broker Health and Start if Down", AutoFix=False)
def check_broker_health(self, host: str):
	self.update_progress(1, "Connecting to Broker")
	broker = Broker(hostname=host)
	self.update_progress(2, "Checking Broker Health")
	if broker.up and broker.connected_to_cluster:
		return "Broker Is UP"
	try:
		broker.start()
	except:
		raise HTTPException(status.HTTP_409_CONFLICT, detail="Broker Is Down, Could Not Start")
	return "Broker Started"