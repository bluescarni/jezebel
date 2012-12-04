import rpc as _rpc, directions as _directions, xmpp as _xmpp

class agent(_rpc.agent,_directions.agent,_xmpp.agent):
	def __init__(self,**kwargs):
		super().__init__(**kwargs)
