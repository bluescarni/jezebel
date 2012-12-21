"""
.. module:: rpc
   :synopsis: RPC base module.

.. moduleauthor::  Francesco Biscani <bluescarni@gmail.com>


"""

class error_codes(object):
	PARSE_ERROR		= -32700
	INVALID_REQUEST		= -32600
	METHOD_NOT_FOUND	= -32601
	INVALID_PARAMS		= -32602
	INTERNAL_ERROR		= -32603

def enable_rpc(method):
	"""Decorator to enable remote calling on methods.
	
	"""
	method._enable_rpc_ = True
	return method

class agent(object):
	def __init__(self,**kwargs):
		import logging
		self.__logger = logging.getLogger('jezebel.rpc.agent')
		self.__logger.info('initialising rpc agent')
		super().__init__(**kwargs)
	@staticmethod
	def translate_rpc_error(code,message):
		if not isinstance(code,int) or not isinstance(message,str):
			raise TypeError('invalid types: code must be an integer and message a string')
		if code in (error_codes.PARSE_ERROR,error_codes.INVALID_REQUEST):
			raise ValueError(message)
		elif code == error_codes.METHOD_NOT_FOUND:
			raise AttributeError(message)
		elif code == error_codes.INVALID_PARAMS:
			raise TypeError(message)
		else:
			raise RuntimeError(message)
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
		
		The request will be parsed into a Python dictionary using the JSON deserializer.
		The method will check that the request conforms to the JSON-RPC 2.0 specification.
		
		"""
		# Return format: error_code, message, parsed_request
		import json
		if not isinstance(s,str):
			raise TypeError('RPC request must be a string')
		try:
			jdict = json.loads(s)
		except:
			return error_codes.PARSE_ERROR, 'parse error', {}
		# No id means it's a notification.
		if 'id' in jdict:
			if not jdict['id'] is None and not isinstance(jdict['id'],(str,int,float)):
				return error_codes.INVALID_REQUEST, 'invalid request: invalid id member type', jdict
		if not 'jsonrpc' in jdict or not isinstance(jdict['jsonrpc'],str) or jdict['jsonrpc'] != '2.0':
			return error_codes.INVALID_REQUEST, 'invalid request: missing or invalid jsonrpc member', jdict
		if not 'method' in jdict or not isinstance(jdict['method'],str):
			return error_codes.INVALID_REQUEST, 'invalid request: missing or invalid method member', jdict
		if 'params' in jdict and not isinstance(jdict['params'],(list,dict)):
			return error_codes.INVALID_REQUEST, 'invalid request: invalid params member', jdict
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
		assert(isinstance(orig_req,dict))
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
			return wrapper(self.__build_jsonrpc_error(error_codes.METHOD_NOT_FOUND,'method not found',jdict))
		# If the method is available, it must have been decorated in order for it to
		# be remotely callable.
		if not hasattr(m,'_enable_rpc_'):
			return wrapper(self.__build_jsonrpc_error(error_codes.METHOD_NOT_FOUND,'method not found',jdict))
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
			return wrapper(self.__build_jsonrpc_error(error_codes.INTERNAL_ERROR,'internal error: ' + repr(e),jdict))
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
				# agent.create_request(), which does not support notifications at the present time.
				assert(not ret is None)
				jdict = self.parse_response(ret)
				# NOTE: since we are interacting with other Python agents, this should always be
				# verified. This check needs to go outside the strict response parsing as it involves
				# the request too.
				assert(jdict['id'] == req['id'])
				if 'error' in jdict:
					self.translate_rpc_error(jdict['error']['code'],jdict['error']['message'])
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
				m = getattr(self,url[0]+'_rpc_request')
			except AttributeError:
				raise TypeError('no handler for scheme "' + url[0] + '" found')
			return m(target,req)
	@enable_rpc
	def urls(self):
		return []
	@enable_rpc
	def features(self):
		return list(filter(lambda _: hasattr(getattr(self,_),'_enable_rpc_'),dir(self)))
	def disconnect(self):
		pass
