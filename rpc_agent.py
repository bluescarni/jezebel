"""
.. module:: rpc_agent
   :synopsis: Base module for the implementation of RPC agents.

.. moduleauthor::  Francesco Biscani <bluescarni@gmail.com>


"""

# TODO: figure a way to document the code property in base exception.

class RPCError(Exception):
	"""Base exception class.
	
	All RPC-related errors derive from this class.
	
	"""
	def __init__(self,code,msg=''):
		"""Constructor.
		
		:param code: an error code
		:type code: integer
		:param msg: an error message
		:type msg: string
		
		:raises: :exc:`TypeError` if the types of *code* and/or *msg* are invalid
		
		"""
		if not isinstance(code,int) or not isinstance(msg,str):
			raise TypeError('invalid argument types')
		self._code = code
		self._msg = msg
	"""String representation.
	
	:rtype: the stored message string
	
	"""
	def __str__(self):
		return self._msg
	@property
	def code(self):
		return self._code

class RPCParseError(RPCError):
	"""RPC parse error.
	
	Will be raised when a JSON-RPC request cannot be parsed.
	
	"""
	def __init__(self):
		"""Constructor.
		
		Will set the internal error code to -32700 as per JSON-RPC 2.0 specification.
		
		"""
		super(RPCParseError,self).__init__(-32700,'error parsing the request')

class RPCInvalidRequestError(RPCError):
	"""RPC parse error.
	
	Will be raised when a JSON-RPC request is malformed.
	
	"""
	def __init__(self,msg=''):
		"""Constructor.
		
		Will set the internal error code to -32600 as per JSON-RPC 2.0 specification.
		
		:param msg: optional additional error info
		:type msg: string
		
		"""
		code = -32600
		if isinstance(msg,str) and msg != '':
			super(RPCInvalidRequestError,self).__init__(code,'invalid request: ' + msg)
		else:
			super(RPCInvalidRequestError,self).__init__(code,'invalid request')

class RPCMethodError(RPCError):
	"""RPC method error.
	
	Will be raised when a method cannot be found.
	
	"""
	def __init__(self):
		"""Constructor.
		
		Will set the internal error code to -32601 as per JSON-RPC 2.0 specification.
		
		"""
		super(RPCMethodError,self).__init__(-32601,'method not found')

class RPCParamsError(RPCError):
	"""RPC parameters error.
	
	Will be raised when the parameters of an RPC are invalid.
	
	"""
	def __init__(self):
		"""Constructor.
		
		Will set the internal error code to -32602 as per JSON-RPC 2.0 specification.
		
		"""
		super(RPCParamsError,self).__init__(-32602,'invalid method parameter(s)')

class RPCInternalError(RPCError):
	"""RPC internal error.
	
	Will be raised in case of an internal JSON-RPC error.
	
	"""
	def __init__(self):
		"""Constructor.
		
		Will set the internal error code to -32603 as per JSON-RPC 2.0 specification.
		
		"""
		super(RPCInternalError,self).__init__(-32603,'internal error')

def enable_rpc(method):
	"""Decorator to enable remote calling on methods.
	
	"""
	method._enable_rpc_ = True
	return method

class agent(object):
	def __init__(self):
		super(agent,self).__init__()
	@staticmethod
	def _translate_rpc_error(jdict):
		# Translate JSON-RPC errors into Python exceptions.
		error_id = jdict['error']['code']
		if error_id == -32700:
			raise RPCParseError
		elif error_id == -32600:
			raise RPCInvalidRequestError(jdict['error']['message'])
		elif error_id == -32601:
			raise RPCMethodError
		elif error_id == -32602:
			raise RPCParamsError
		else:
			raise RPCInternalError
	@staticmethod
	def create_request(method_name,*args,**kwargs):
		"""Create RPC request from signature.
		
		"""
		import uuid, json
		if not isinstance(method_name,str):
			raise TypeError('method name must be a string')
		if len(args) != 0 and len(kwargs) != 0:
			raise TypeError('the method cannot be called with positional and keyword arguments at the same time')
		# Start building the dict.
		jdict = {'jsonrpc':'2.0','id':str(uuid.uuid4()),'method':method_name}
		if len(args) != 0:
			jdict['params'] = args
		elif len(kwargs) != 0:
			jdict['params'] = kwargs
		return jdict
	@staticmethod
	def parse_request(s):
		"""Parse RPC request.
		
		The request will be parsed into a Python dictionary using the JSON deserialized.
		The method will check that the request conforms to the JSON-RPC 2.0 specification.
		
		"""
		# Return format: error_code, message, parsed_request
		import json
		if not isinstance(s,str):
			raise TypeError('RPC request must be a string')
		try:
			jdict = json.loads(s)
		except:
			return -32700, 'parse error', {}
		# No id means it's a notification.
		if 'id' in jdict:
			if not jdict['id'] is None and not isinstance(jdict['id'],(str,int,float)):
				return -32600, 'invalid request: invalid id member type', jdict
		if not 'jsonrpc' in jdict or not isinstance(jdict['jsonrpc'],str) or jdict['jsonrpc'] != '2.0':
			return -32600, 'invalid request: missing or invalid jsonrpc member', jdict
		if not 'method' in jdict or not isinstance(jdict['method'],str):
			return -32600, 'invalid request: missing or invalid method member', jdict
		if 'params' in jdict and not isinstance(jdict['params'],(list,dict)):
			return -32600, 'invalid request: invalid params member', jdict
		return None, '', jdict
	@staticmethod
	def parse_response(s):
		import json
		if not isinstance(s,str):
			raise TypeError('RPC response must be a string')
		jdict = json.loads(s)
		if not 'jsonrpc' in jdict or not isinstance(jdict['jsonrpc'],str) or jdict['jsonrpc'] != '2.0':
			raise ValueError('missing/invalid jsonrpc value in response')
		if not 'id' in jdict or (not isinstance(jdict['id'],(str,int,float)) and not jdict['id'] is None):
			raise ValueError('missing/invalid id value in response')
		if int('result' in jdict) + int('error' in jdict) != 1:
			raise ValueError('either a result or an error (but not both) must be present in the response')
		if 'error' in jdict:
			if not jdict['id'] is None:
				raise ValueError('in case of errors the id of the response must be null')
			if not isinstance(jdict['error'],dict):
				raise ValueError('the error value must be an object')
			if not 'code' in jdict['error'] or not isinstance(jdict['error']['code'],int):
				raise ValueError('missing/invalid error code')
			if not 'message' in jdict['error'] or not isinstance(jdict['error']['message'],str):
				raise ValueError('missing/invalid error message')
		return jdict
	@staticmethod
	def __build_jsonrpc_error(code,message,orig_req):
		import json
		assert(isinstance(code,int))
		assert(isinstance(message,str))
		assert(isinstance(dict,orig_req))
		retval = {'jsonrpc':'2.0'}
		# NOTE: here we have to test the type of the id field as we might end up calling this method
		# with an invalid id type.
		if 'id' in orig_req and ((orig_req['id'] is None) or isinstance(orig_req['id'],(str,int,float))):
			retval['id'] = orig_req['id']
		else:
			retval['id'] = None
		retval['error'] = {'code' : code, 'message' : message}
		return json.dumps(retval)
	def execute_request(self,s):
		"""Execute RPC request.
		
		The request *s*, in string form, will be first parsed using :func:`parse_request`, and then dispatched
		to one of the agent object's methods. If the request is a notification, this method will return ``None``,
		otherwise the return value of the invoked method will be returned translated into the string
		representation of a JSON-RPC response object.
		
		"""
		import json
		# This is the only error we want to raise, apart from assertions.
		# All other errors get returned as JSON-RPC errors.
		if not isinstance(s,str):
			raise TypeError('RPC request must be a string')
		error_code, message, jdict = self.parse_request(s)
		# NOTE: when there's an error at the parsing/validation level, we always reply
		# even if the request might have looked like a notification (i.e., an invalid request is not a notification).
		# The id of the response in this case is the one in jdict, if it could be recovered, or None.
		if not error_code is None:
			return self.__build_jsonrpc_error(error_code,message,jdict)
		# At this point, the request is valid.
		# Build little helper function to return None instead of something if the request is a notification.
		def wrapper(retval):
			if 'id' in jdict:
				return retval
		# Try to get the method.
		try:
			m = getattr(self,jdict['method'])
		except AttributeError:
			return wrapper(self.__build_jsonrpc_error(-32601,'method not found',jdict))
		# If the method is available, it must have been decorated in order for it to
		# be remotely callable.
		if not hasattr(m,'_enable_rpc_'):
			return wrapper(self.__build_jsonrpc_error(-32601,'method not found',jdict))
		try:
			# Call with the appropriate parameter unpacking (or no params at all).
			if 'params' in jdict:
				if isinstance(jdict['params'],list):
					retval = m(*jdict['params'])
				else:
					assert(isinstance(jdict['params'],dict))
					retval = m(**jdict['params'])
			else:
				retval = m()
			return wrapper(json.dumps({'jsonrpc':'2.0','id':jdict['id'],'result':retval}))
		except BaseException as e:
			# NOTE: Pokemon exception handling in case something gets raised calling the method
			# or serialising the result. This could be made more specific, at least in case of
			# invalid function signature parameters when calling the method. Eventually, might use
			# the inspect module for that.
			return wrapper(self.__build_jsonrpc_error(-32603,'internal error: ' + repr(e),jdict))
	def __call__(self,target,method_name,*args,**kwargs):
		import json
		from concurrent.futures import ThreadPoolExecutor as tpe
		# Target must be a string or another agent.
		if not isinstance(target,str) and not isinstance(target,agent):
			raise TypeError('the target must be either a URL in string form or an agent instance')
		# Create the request.
		req = self.create_request(method_name,*args,**kwargs)
		if isinstance(target,agent):
			# Define the worker function.
			def worker():
				ret = target.execute_request(json.dumps(req))
				# NOTE: ret cannot be None because we constructed the request with
				# agent.create_request(), which does not support notifications.
				assert(not ret is None)
				jdict = self.parse_response(ret)
				# NOTE: since we are interacting with other Python agents, this should always be
				# verified. This check needs to go outside the strict response parsing as it involves
				# the request too.
				assert(jdict['id'] == req['id'])
				if 'error' in jdict:
					self._translate_rpc_error(jdict)
				else:
					return jdict['result']
			executor = tpe(max_workers = 1)
			retval = executor.submit(worker)
			executor.shutdown(wait = False)
			return retval
		else:
			from urllib.parse import urlparse
			url = urlparse(target)
			if url[0] == '':
				raise ValueError('no scheme detected in URL')
			try:
				m = getattr(self,url[0]+'_call_request')
			except AttributeError:
				raise TypeError('no handler for scheme "' + url[0] + '" found')
			return m(target,req)
	def hello_wrong(self):
		pass
	@enable_rpc
	def hello_empty(self):
		pass
	@enable_rpc
	def hello_world(self):
		return 'hello world'
