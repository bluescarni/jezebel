import rpc as _rpc

class agent(object):
	def __init__(self,**kwargs):
		import logging
		self.__logger = logging.getLogger('jezebel.directions.agent')
		super().__init__(**kwargs)
	@_rpc.enable_rpc
	def get_directions(self,origin,destination):
		import urllib, json
		if not isinstance(origin,str) or not isinstance(destination,str):
			raise TypeError('origin and destination must be strings')
		base_address = r'http://maps.googleapis.com/maps/api/directions/json'
		url = base_address + '?' + urllib.parse.urlencode({'origin':origin,'destination':destination,'sensor':'false'})
		self.__logger.info('requesting url: ' + url)
		result = json.loads(urllib.request.urlopen(url).read().decode('utf-8'))
		if result['status'] != 'OK':
			raise RuntimeError('the directions request failed, full output is: ' + repr(result))
		return result
	@staticmethod
	def show_route(route):
		import PyQt4.QtGui, PyQt4.QtWebKit, PyQt4.QtCore
		step_list = [step['html_instructions'] for step in route['routes'][0]['legs'][0]['steps']]
		class Window(PyQt4.QtGui.QWidget):
			def __init__(self):
				super(Window, self).__init__()
				view = PyQt4.QtWebKit.QWebView(self)
				layout = PyQt4.QtGui.QVBoxLayout(self)
				layout.addWidget(view)
				html = '<!DOCTYPE html><html><head><title>Route</title></head><body>\n' + route['routes'][0]['copyrights'] + '\n<ol>\n'
				for step in step_list:
					html += '<li>' + step + '</li>\n'
				html += '</ol></body></html>'
				print(html)
				view.setHtml(html)
		window = Window()
		window.show()
		return window
