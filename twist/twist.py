'''
version: 0.2
'''

from webob import Request
import types
from urllib import urlencode
from urlparse import parse_qs

METHODS = ['get','post','put','delete']

def get_route_name(route, method):
	return 'route_' + route + '_' + method.lower()

##----------------------------------------------------------------##
class Base(type):
    def __new__(cls, name, bases, dct):
    	route = dct.get('__alias__', name.lower())
    	for base in bases:
    		if base.__name__ == 'Twist':
    			for method in METHODS:
    				if method in dct:
    					func_name = get_route_name(route,method)
    					if hasattr(base, func_name):
    						raise Exception(func_name + 'Function already exists.')
    					setattr(base, func_name, dct[method])
        return type.__new__(cls, name, bases, dct)

##----------------------------------------------------------------##

class Twist(object):
	__metaclass__ = Base

	@classmethod
	def run(self, port=8000, key=None):
		from wsgiref.simple_server import make_server
		server = make_server('', port, self)
		print 'serving on port', port
		server.serve_forever()

	def __init__(self, env, start_response):
		self.request = Request(env)
		self.start_response = start_response

		#
		# Get name, params and verify name exists
		#
		frags = env['PATH_INFO'].strip('/').split('/')
		name = get_route_name(frags[0], self.request.method)
		self.params = frags[1:]
		if not hasattr(self, name):
			raise Exception('Method not found:'+name)
		
		#
		# Get query strings and save into keyword parameters
		#
		qs_pairs = parse_qs(self.request.query_string).items()
		self.kw_params = { k:v[0] if len(v)==1 else v for k,v in qs_pairs }

		#
		# Execute routed method and save to output
		#
		try:
			self.output = getattr(self,name)(*self.params, **self.kw_params)
		except Exception as ex:
			print '> Error executing', name, ex

	def __iter__(self):
		self.start_response('200 OK', [('Content-type', 'text/plain')])
		yield "Hello world"



##----------------------------------------------------------------##

##----------------------------------------------------------------##
