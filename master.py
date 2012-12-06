from . import rpc as _rpc

class agent(object):
	def __init__(self,**kwargs):
		from threading import Lock
		import logging
		super().__init__(**kwargs)
		self.__logger = logging.getLogger('jezebel.master.agent')
		self.__logger.info('initialising master agent')
		self.__agent_list = []
		self.__lock = Lock()
	def __wrap_url_request(self,agent):
		try:
			return agent.urls()
		except:
			return None
	@_rpc.enable_rpc
	def spawn(self,t,*args,**kwargs):
		import importlib
		if not isinstance(t,str):
			raise TypeError('agent type must be a string')
		try:
			m = importlib.import_module('..' + t,'jezebel.master')
			self.__logger.info('attempting to spawn an agent of type "' + t + '"')
			with self.__lock:
				self.__agent_list.append(m.agent(*args,**kwargs))
				retval = self.__wrap_url_request(__agent_list[-1])
			return retval
		except (ImportError, AttributeError):
			raise TypeError('invalid agent type')
	@_rpc.enable_rpc
	def agent_urls(self):
		with self.__lock:
			return [self.__wrap_url_request(a) for a in self.__agent_list]
