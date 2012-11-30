from rpc_agent import agent as _agent
import logging as _log

# test_xmpp_agent1
# test_xmpp_agent2
class agent(_agent):
	def __start(self,event):
		self.__xmpp_client.send_presence()
		self.__xmpp_client.get_roster()
		with self.__tmp_cv:
			self.__tmp_status = 1
			self.__logger.info('session started')
			self.__tmp_cv.notify_all()
	def __failed_auth(self,event):
		with self.__tmp_cv:
			self.__tmp_status = -1
			logging.info('authentication failure')
			self.__tmp_cv.notify_all()
	def __message(self,msg):
		self.__logger.info('received message')
		if not msg['type'] in ('normal','chat'):
			# Do nothing if the message is not a normal or chat one.
			self.__logger.info('message of type "' + msg['type'] + '" will not be handled')
			return
		self.__logger.info('message of type "' + msg['type'] + '" will be handled')
		self.__logger.info('message body:\n' + msg['body'])
		# First try to see if the message is a response.
		try:
			jdict = self.parse_response(msg['body'])
			is_response = True
		except:
			is_response = False
		if is_response:
			self.__logger.info('message parsed as response')
			with self.__cv:
				if jdict['id'] in self.__pending_requests:
					self.__logger.info('matching pending request found')
					self.__received_responses[jdict['id']] = jdict
					del self.__pending_requests[jdict['id']]
					self.__cv.notify_all()
				else:
					self.__logger.info('no matching pending request found, ignoring message')
			return
		self.__logger.info('attempting to execute request')
		# Interpret as a request, execute and reply the answer, if the request was not a notification.
		ret = self.execute_request(msg['body'])
		if not ret is None:
			msg.reply(ret).send()
	def __init__(self,jid,password,timeout = None):
		from sleekxmpp import ClientXMPP
		from threading import Condition, Lock
		import ssl
		super(agent,self).__init__()
		if timeout is None:
			self.__timeout = None
		else:
			try:
				self.__timeout = float(timeout)
			except:
				raise TypeError('cannot convert timeout value to float')
			if self.__timeout < 0.:
				raise ValueError('timeout value must be non-negative')
		# Logger object.
		self.__logger = _log.getLogger('jezebel.xmpp.agent')
		self.__logger.info('creating an agent')
		# Create the XMPP client as a class member.
		self.__xmpp_client = ClientXMPP(jid,password)
		# Dictionary of sent requests and received responses.
		self.__pending_requests = {}
		self.__received_responses = {}
		# Global lock and condition variable.
		self.__lock = Lock()
		self.__cv = Condition(self.__lock)
		# The SSL setting is needed for openfire.
		self.__xmpp_client.ssl_version = ssl.PROTOCOL_SSLv3
		# Add event handlers.
		self.__xmpp_client.add_event_handler('session_start',self.__start)
		self.__xmpp_client.add_event_handler('failed_auth',self.__failed_auth)
		self.__xmpp_client.add_event_handler('message',self.__message)
		# Iinitiate the connection and move to background.
		self.__tmp_cv = Condition()
		self.__tmp_status = 0
		if self.__xmpp_client.connect():
			self.__xmpp_client.process(block=False)
			with self.__tmp_cv:
				while self.__tmp_status == 0:
					self.__tmp_cv.wait()
				s = self.__tmp_status
			if s == -1:
				self.__xmpp_client.disconnect()
				raise RuntimeError('authentication failure')
		else:
			raise RuntimeError('connection failed')
		self.client = self.__xmpp_client
	def xmpp_disconnect(self):
		self.__xmpp_client.disconnect()
	def xmpp_rpc_request(self,target,req):
		from urllib.parse import urlparse
		import json
		from concurrent.futures import ThreadPoolExecutor as tpe
		jid = urlparse(target)[1]
		req_s = json.dumps(req)
		# First the request must be registered, then sent. The other way around,
		# we might get a reply before the request is registered.
		with self.__lock:
			self.__pending_requests[req['id']] = req
		# NOTE: try-catch because if something fails here we need to remove
		# the request from the pending requests list.
		try:
			self.__logger.info('sending request to ' + jid)
			self.__xmpp_client.send_message(mto=jid,mbody=req_s)
		except:
			with self.__lock:
				# Unlikely, but it could be possible the a request with the same id got satisfied in the meantime.
				if req['id'] in self.__pending_requests:
					del self.__pending_requests[req['id']]
			raise
		# Async worker function.
		def worker():
			from time import time
			start = time()
			with self.__cv:
				self.__logger.info('listening for response')
				while not req['id'] in self.__received_responses:
					if not self.__timeout is None and time() - start > self.__timeout:
						# Remove the pending request.
						if req['id'] in self.__pending_requests:
							del self.__pending_requests[req['id']]
						raise RuntimeError('timeout')
					self.__cv.wait(self.__timeout)
				jdict = self.__received_responses.pop(req['id'])
			if 'error' in jdict:
				self.translate_rpc_error(jdict['error']['code'],jdict['error']['message'])
			else:
				return jdict['result']
		executor = tpe(max_workers = 1)
		retval = executor.submit(worker)
		executor.shutdown(wait = False)
		return retval
	@property
	def xmpp_pending(self):
		from copy import deepcopy
		with self.__lock:
			return deepcopy(self.__pending_requests)
	@property
	def xmpp_received(self):
		from copy import deepcopy
		with self.__lock:
			return deepcopy(self.__received_responses)
