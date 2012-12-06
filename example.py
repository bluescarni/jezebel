from . import rpc as _rpc, directions as _directions, xmpp as _xmpp, master as _master

class agent(_rpc.agent,_directions.agent,_xmpp.agent,_master.agent):
	def __init__(self,**kwargs):
		import logging
		super().__init__(**kwargs)
		self.__logger = logging.getLogger('jezebel.example.agent')
		self.__logger.info('initialising example agent')
