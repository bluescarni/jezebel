from . import rpc as _rpc

def _check_inheritance(self):
	if not issubclass(type(self),_rpc.agent):
		raise TypeError('this class must be a subclass of the rpc agent class')
