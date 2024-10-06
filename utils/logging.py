from elasticsearch import Elasticsearch
import logging
from time import time

class ElasticsearchHandler(logging.Handler):
	def __init__(self, urls, index, username, password):
		super().__init__()
		self.urls = urls
		self.index = index
		self.username = username
		self.password = password
		self.connection = Elasticsearch(hosts=self.urls, http_auth=(self.username, self.password), verify_certs=False, ssl_show_warn=False)

	def emit(self, record):
		try:
			msg = self.format(record)
			self.connection.index(index=self.index, body=msg)
		except Exception as e:
			print(f"Couldn't Index Log: {e}")

	def format(self, record):
		return {
			'message': record.getMessage(),
			'level': record.levelname,
			'@timestamp': int(time()),
			'automation_id': getattr(record, 'id', None),
			'name': getattr(record, 'automation_name', None),
			'progress': getattr(record, 'progress', None),
			'parameters': getattr(record, 'parameters', None),
			'state': getattr(record, 'state', None)
		}