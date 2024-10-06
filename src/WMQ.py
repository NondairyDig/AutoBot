
from .Host import Host
from ..config import VICTORIA_QUERY_METRICS_URL, REQUESTS_CLIENT, DEFAULT_MQ_CHANNEL, MQ_AUTH
from fastapi import HTTPException, status
from pydantic import constr
import pymqi


class QMGR(Host):
	qm: constr(max_length=256) = None
	listen_port: constr(max_length=256) = None
	version: constr(max_length=256) = None
	pymqi_handler: pymqi.QueueManager = None

	def __init__(self, **kwargs):
		super().__init__(**kwargs)
		self.get_connection_details()

	class Config:
		arbitrary_types_allowed = True

	def get_connection_details(self):
		info = REQUESTS_CLIENT.get(VICTORIA_QUERY_METRICS_URL + f"wmq_qmgr_info{{queue_manager='{self.qu}'}}").json()
		if not info['data']['result']:
			raise HTTPException(status=status.HTTP_404_NOT_FOUND, detail="Queue Manager Not Found")
		self.listen_port = info['data']['result'][0]['metric']['port']
		self.hostname = info['data']['result'][0]['metric']['host']
		if not self.ip:
			self.dns_to_ip()

	def get_qm_by_host(self):
		info = REQUESTS_CLIENT.get(VICTORIA_QUERY_METRICS_URL + f"wmq_qmgr_info{{host='{self.hostname}'}}").json()
		self.qu = info['data']['result'][0]['metric']['queue_manager']

	def connect(self):
		if self.pymqi_handler:
			if self.pymqi_handler.is_connected:
				return "Already Connected"
		if not self.qm and self.hostname:
			self.get_qm_by_host()
		if not self.ip or not self.hostname:
			self.get_connection_details()
		if not self.ip or not self.listen_port:
			raise Exception("Not Enough Details For QMGR Connection")
		self.pymqi_handler = pymqi.connect(self.qm, DEFAULT_MQ_CHANNEL, f"{self.ip}({self.listen_port})")

	def disconnect(self):
		self.pymqi_handler.disconnect()

	def reset_channel(self, channel_name):
		mq_pcf_exec = pymqi.PCFExecute(self.pymqi_handler)
		channel_config = {
			pymqi.CMQCFC.MQCACH_CHANNEL_NAME: channel_name,
		}
		mq_pcf_exec.MQCHD_RESET_CHANNEL(channel_config)
		return True

	def restore_from_diq(self):
		self._connect_and_execute_no_output(MQ_AUTH["username"], MQ_AUTH["password"],
											f"pkill -9 .*runmqdlq.*; echo 'ACTION (RETRY)' | timeout -s 9 6s /opt/mqm/bin/runmqdlq SYSTEM.DEAD.LETTER.QUEUE {self.qm}")
		return True