from . import rpc as _rpc, _detail

class agent(object):
	def __init__(self,**kwargs):
		from threading import Lock
		import logging
		_detail._check_inheritance(self)
		self.__logger = logging.getLogger('jezebel.master.agent')
		self.__logger.info('initialising master agent')
		self.__agent_list = []
		self.__lock = Lock()
		super().__init__(**kwargs)
	@_rpc.enable_rpc
	def spawn(self,t,*args,**kwargs):
		import importlib
		if not isinstance(t,str):
			raise TypeError('agent type must be a string')
		try:
			self.__logger.info('attempting to spawn an agent of type "' + t + '"')
			m = importlib.import_module('..' + t,'jezebel.master')
			a_type = m.agent
		except (ImportError,AttributeError):
			raise TypeError('no agent type "' + t + '" found')
		new_agent = a_type(*args,**kwargs)
		retval = new_agent.urls()
		with self.__lock:
			self.__agent_list.append(new_agent)
		return retval
	@_rpc.enable_rpc
	def agent_urls(self):
		with self.__lock:
			return [a.urls() for a in self.__agent_list]
