'''
version: 0.2
'''

import os
import sys
import types
import traceback
from webob import Request, Response, static
from urllib import urlencode
from urlparse import parse_qs, urljoin

LOGGING = True
DEV = True
APP_DIR = '.'

##----------------------------------------------------------------##
METHODS = ['get','post','put','delete']

def get_route_name(route, method):
	return 'route_' + route + '_' + method.lower()
class Interrupt (Exception):
	pass

##----------------------------------------------------------------##
class Base(type):
    def __new__(cls, name, bases, dct):
    	route = dct.get('route', name.lower())
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

class Twist (object):
	__metaclass__ = Base

	def __init__(self, env, start_response):
		self.env = env
		self.start_response = start_response
		self.request = Request(env)
		self.response = Response()

		try:
			if self.request.method == 'HEAD': return

			frags = env['PATH_INFO'].strip('/').split('/')

			# Get name, params and verify name exists
			#
			name = get_route_name(frags[0], self.request.method)
			self.params = frags[1:]
			if not hasattr(self, name):
				self.error(404, 'Not found: '+frags[0])
			
			# Save query strings into keyword parameters
			#
			qs_pairs = parse_qs(self.request.query_string).items()
			self.kw_params = { k:v[0] if len(v)==1 else v for k,v in qs_pairs }

			# Execute routed method and save to output
			#
			self.response.body = getattr(self,name)(*self.params, **self.kw_params)
		except Interrupt as ex: 
			pass
		except:
			self.cleanup()

	def __iter__(self):
		self.start_response(self.response.status, self.response.headers.items())
		yield self.response.body

	def static_file(self, filename):
		file_app = static.FileApp(filename)
		self.response = self.request.get_response(file_app)
		raise Interrupt()

	def error(self, code=500, mesg=''):
		self.response.status = code
		self.response.body = mesg
		raise Interrupt()

	def cleanup(self):
		mesg = traceback.format_exc() if DEV else 'Error executing app'
		self.response.status = 500
		self.response.body = mesg
		if DEV:
			print mesg

	def redirect(self, url, code=None):
	    self.response.status = code if code else 303 if self.request.http_version == "HTTP/1.1" else 302
	    self.response.location = urljoin(self.request.url, url)
	    raise Interrupt()

##----------------------------------------------------------------##

def run(port=8000, key=None):
	from wsgiref.simple_server import make_server
	server = make_server('', port, Twist)
	print 'serving on port', port
	server.serve_forever()
##----------------------------------------------------------------##
