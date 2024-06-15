from .Host import Host
from pydantic import constr

class Zookeeper:
	listen_port: constr(max_length=5) = "2181"

	def echo():
		return True