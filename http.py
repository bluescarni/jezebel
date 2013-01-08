from . import _detail, rpc as _rpc
import http.server as _server, threading as _thr
from socketserver import ThreadingMixIn as _thr_mixin

class _req_handler(_server.BaseHTTPRequestHandler):
	# Use 1.0 as it is most minimialist (no mandatory header parts).
	protocol_version = "HTTP/1.0"
	def __init__(self,*args,**kwargs):
		import logging
		self.__logger = logging.getLogger('jezebel.http.agent')
		super().__init__(*args,**kwargs)
	def __return_client_error(self,code,msg):
		self.send_response(code)
		self.send_header('Content-type','text/plain; charset="utf-8"')
		self.end_headers()
		self.wfile.write(msg.encode('utf-8'))
	def do_GET(self):
		self.send_response(200)
		self.send_header('Content-type','html')
		self.end_headers()
		self.wfile.write(bytes('<!DOCTYPE html><html><head><title>Hey there!</title></head><body><p>I am an agent \o/</p></body></html>','utf-8'))
	def do_POST(self):
		try:
			length = int(self.headers['Content-Length'])
			c_type = self.headers['Content-type']
			a_type = self.headers['Accept']
			req = self.rfile.read(length).decode('utf-8')
		except BaseException as e:
			return self.__return_client_error(400,'Exception caught while examining the HTTP header: ' + repr(e))
		self.__logger.info('received POST request:\n' + req)
		if not 'application/json' in c_type:
			return self.__return_client_error(400,'Invalid content type "' + c_type + '" in request (it should contain "application/json")')
		if not 'application/json' in a_type:
			return self.__return_client_error(400,'Invalid acceptable content type "' + a_type + '" in request (it should contain "application/json")')
		retval = self.server.agent.execute_request(req)
		self.send_response(200)
		self.send_header('Content-type','application/json')
		self.end_headers()
		if not retval is None:
			self.__logger.info('replying with:\n' + retval)
			self.wfile.write(retval.encode('utf-8'))

class _mt_http_server(_thr_mixin,_server.HTTPServer):
	pass

class _thr_server(_thr.Thread):
	def __init__(self,server_address,req_handler):
		import logging
		self.__logger = logging.getLogger('jezebel.http.agent')
		self.server = _mt_http_server(server_address,_req_handler)
		super().__init__()
	def run(self):
		self.__logger.info('starting HTTP server at address ' + str(self.server.server_address))
		self.server.serve_forever()

class agent(object):
	def __init__(self,server_address = None,http_timeout = 10.,**kwargs):
		import logging
		_detail._check_inheritance(self)
		if http_timeout is None:
			self.__timeout = None
		else:
			try:
				self.__timeout = float(http_timeout)
			except:
				raise TypeError('cannot convert timeout value to float')
			if self.__timeout < 0.:
				raise ValueError('timeout value must be non-negative')
		self.__logger = logging.getLogger('jezebel.http.agent')
		self.__logger.info('initialising http agent')
		self.__logger.info('timeout set to ' + str(self.__timeout))
		# Create the server object only if requested.
		if not server_address is None:
			# Create the threaded server object.
			self.__server = _thr_server(server_address,_req_handler)
			# Make the agent reachable from the server.
			self.__server.server.agent = self
			# Start the server.
			self.__server.start()
		try:
			super().__init__(**kwargs)
		except:
			self.__disconnect()
			raise
	def __disconnect(self):
		self.__logger.info('disconnecting http agent')
		try:
			self.__server.server.server_close()
			self.__server.server.shutdown()
			self.__logger.info('server has been shut down')
		except AttributeError:
			pass
	@_rpc.enable_rpc
	def urls(self):
		try:
			a = self.__server.server.server_address
			return [r'http://' + a[0] + ":" + str(a[1])] + super().urls()
		except AttributeError:
			return super().urls()
	def disconnect(self):
		self.__disconnect()
		super().disconnect()
	def http_rpc_request(self,target,req):
		import urllib.request, json
		from concurrent.futures import ThreadPoolExecutor as tpe
		h = {'Content-type':'application/json', 'Accept':'application/json'}
		r = urllib.request.Request(url=target,data=json.dumps(req).encode('utf-8'),headers=h)
		def worker():
			jdict = self.parse_response(urllib.request.urlopen(r,timeout = self.__timeout).read().decode('utf-8'))
			if 'error' in jdict:
				self.translate_rpc_error(jdict['error']['code'],jdict['error']['message'])
			else:
				return jdict['result']
		executor = tpe(max_workers = 1)
		retval = executor.submit(worker)
		executor.shutdown(wait = False)
		return retval
