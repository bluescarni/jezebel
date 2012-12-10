from . import rpc as _rpc, directions as _directions, xmpp as _xmpp, master as _master

class agent(_xmpp.agent,_directions.agent,_master.agent,_rpc.agent):
	def __init__(self,**kwargs):
		import logging
		self.__logger = logging.getLogger('jezebel.example.agent')
		self.__logger.info('initialising example agent')
		super().__init__(**kwargs)
