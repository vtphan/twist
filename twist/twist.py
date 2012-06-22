'''
version: 0.2
'''

import os
import sys
import types
import traceback
import threading
from webob import Request, Response, static
from urllib import urlencode
from urlparse import parse_qs, urljoin
from jinja2 import Environment, PackageLoader

LOGGING = True
DEV = True
APP_DIR = '.'
TEMPLATE_DIR = './template'
STATIC_DIR = './static'

jinja_env = Environment(loader=PackageLoader('twist', TEMPLATE_DIR))

##----------------------------------------------------------------##
METHODS = ['get','post','put','delete']

class Interrupt (Exception):
	pass

##----------------------------------------------------------------##
class Route(object):
	table = {}

	@classmethod
	def set(self, path, cls):
		if path in self.table: raise Exception('route:',path,'exists.')
		self.table[path] = cls

	@classmethod
	def get(self, path):
		return self.table[path] if path in self.table else None

	@classmethod
	def show(self):
		print 'Route.table:', self.table,'\n'

##----------------------------------------------------------------##
class Base(type):
	def __new__(cls, name, bases, dct):
		new_class = type.__new__(cls, name, bases, dct)
		if name != 'App':
			handle = dct.get('alias', name.lower())
			Route.set(handle, new_class)

			t_file = dct.get('template', None)
			template = jinja_env.get_template(t_file) if t_file else None
			setattr(new_class, '_template', template)
			
		return new_class

##----------------------------------------------------------------##

class App (object):
	__metaclass__ = Base

	def __init__(self, env):
		self.request = Request(env)
		self.response = Response()

	def static_file(self, filename):
		file_app = static.FileApp(os.path.join(STATIC_DIR, filename))
		self.response = self.request.get_response(file_app)
		raise Interrupt()

	def error(self, code=500, mesg=''):
		self.response.status = code
		self.response.body = mesg
		raise Interrupt()

	def redirect(self, url, code=None):
		self.response.status = code if code else 303 if self.request.http_version == "HTTP/1.1" else 302
		self.response.location = urljoin(self.request.url, url)
		raise Interrupt()

	def render(self, **kw):
		if not hasattr(self, '_template'):
			self.error(404, 'Template Not found')
		self.response.content_type = 'text/html'
		self.response.charset = 'utf-8'
		return self._template.render(**kw)


class Twist (object):

	def __init__(self, env, start_response):
		start_response = start_response

		try:

			frags = env['PATH_INFO'].strip('/').split('/')

			controller = Route.get(frags[0])
			if not controller:
				self.error(404, 'Controller not found: '+frags[0])
			method = env['REQUEST_METHOD'].lower()
			if method == 'HEAD': return
			if not hasattr(controller, method):
				self.error(404, 'Method not allow: '+env['REQUEST_METHOD'])

			app = controller(env)

			# Get params and kw_params
			#
			params = frags[1:]
			qs_pairs = parse_qs(app.request.query_string).items()
			kw_params = { k:v[0] if len(v)==1 else v for k,v in qs_pairs }

			# Execute routed method and save to output
			#
			output = getattr(app,method)(*params, **kw_params)
			if isinstance(output,unicode): app.response.text  = output
			else: app.response.body = output
		except Interrupt as ex: 
			pass
		except:
			app.response.status = 500
			app.response.body =  traceback.format_exc() if DEV else 'Error executing app'
			if DEV: 
				print app.response.body
		start_response(app.response.status, app.response.headers.items())
		self.response = threading.local()
		self.response.body = app.response.body

	def __iter__(self):
		yield self.response.body


##----------------------------------------------------------------##

def run(port=8000, key=None):
	from wsgiref.simple_server import make_server
	server = make_server('', port, Twist)
	print 'serving on port', port
	server.serve_forever()
##----------------------------------------------------------------##
