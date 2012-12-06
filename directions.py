from . import rpc as _rpc

class agent(object):
	def __init__(self,**kwargs):
		import logging
		super().__init__(**kwargs)
		self.__logger = logging.getLogger('jezebel.directions.agent')
		self.__logger.info('initialising directions agent')
	@_rpc.enable_rpc
	def get_directions(self,origin,destination):
		import urllib, urllib.request, json
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
		import re, PyQt4.QtGui, PyQt4.QtWebKit, PyQt4.QtCore
		step_list = [step['html_instructions'] for step in route['routes'][0]['legs'][0]['steps']]
		# Vertices of the bounding box.
		bb = route['routes'][0]['bounds']
		sw = [bb['southwest'][k] for k in bb['southwest']]
		ne = [bb['northeast'][k] for k in bb['northeast']]
		# Encoded polyline.
		# NOTE: this needs to be escaped for literal substitution.
		epl = re.escape(route['routes'][0]['overview_polyline']['points'])
		class Window(PyQt4.QtGui.QWidget):
			def __init__(self):
				super().__init__()
				self.__layout = PyQt4.QtGui.QHBoxLayout(self)
				self.__view_directions = PyQt4.QtWebKit.QWebView(self)
				html = '<!DOCTYPE html><html><head><title>Route</title></head><body>\n' + route['routes'][0]['copyrights'] + '\n<ol>\n'
				for step in step_list:
					html += '<li>' + step + '</li>\n'
				html += '</ol></body></html>'
				self.__view_directions.setHtml(html)
				self.__view_map = PyQt4.QtWebKit.QWebView(self)
				self.__view_map.settings().setAttribute(PyQt4.QtWebKit.QWebSettings.JavascriptEnabled,True)
				html = """
					<!DOCTYPE html>
					<html>
					<head><title>Map view</title>
					<meta name="viewport" content="initial-scale=1.0, user-scalable=no" />
					<style type="text/css">
					html { height: 100%% }
					body { height: 100%%; margin: 0; padding: 0 }
					#map_canvas { height: 100%% }
					</style>
					<script type="text/javascript"
					src="https://maps.googleapis.com/maps/api/js?libraries=geometry&amp;sensor=false">
					</script>
					<script type="text/javascript">
					function initialize() {
						// Define the two corners of the bounding box.
						var sw = new google.maps.LatLng(%f,%f);
						var ne = new google.maps.LatLng(%f,%f);
						// Create a bounding box.
						var bounds = new google.maps.LatLngBounds(sw, ne);
						// Map options.
						var mapOptions = {
							center: bounds.getCenter(),
							zoom: 8,
							mapTypeId: google.maps.MapTypeId.ROADMAP
						};
						var map = new google.maps.Map(document.getElementById("map_canvas"),
							mapOptions);
						// Make the map fit the bounds from directions.
						map.fitBounds(bounds);
						// Decode the polyline.
						var decodedPath = google.maps.geometry.encoding.decodePath("%s");
						polyLine = new google.maps.Polyline({
							path: decodedPath,
							strokeColor: "#FF0000",
							strokeOpacity: 1.0,
							strokeWeight: 2,
							geodesic: true,
							map: map
						});
					}
					</script>
					</head>
					<body onload="initialize()">
					<div id="map_canvas" style="width:100%%; height:100%%"></div>
					</body>
					</html>
				""" % (sw[0],sw[1],ne[0],ne[1],epl)
				self.__view_map.setHtml(html)
				self.__layout.addWidget(self.__view_directions)
				self.__layout.addWidget(self.__view_map)
		window = Window()
		window.show()
		return window
