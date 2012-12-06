from . import rpc as _rpc

def _check_inheritance(self):
	if not isinstance(self,_rpc.agent):
		raise TypeError('this class must derive from the rpc agent class')
