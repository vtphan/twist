'''
package: twist
version: testing
author: Vinhthuy Phan
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

def extract_vars(form):
	d = {}
	for key, value in form.items():
		if isinstance(value,list) and len(value)==1:
			value = value[0]
		if not key in d:
			d[key] = value
		elif isinstance(d[key],list):
			d[key].append(value)
		else:
			d[key]=[d[key],value]
	return d

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

	def head(self, *arg, **kw_arg):
		return ''

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

##----------------------------------------------------------------##

class Twist (object):

	def __init__(self, env, start_response):
		self.start_response = start_response
		self.response = threading.local()

		try:
			frags = env['PATH_INFO'].strip('/').split('/')

			controller = Route.get(frags[0])
			method = env['REQUEST_METHOD'].lower()
			if not controller or not hasattr(controller, method):
				self.flush('404 Not Found', 'Not found: '+frags[0]+' '+env['REQUEST_METHOD'])
				return

			app = controller(env)

			# Get params and kw_params
			#
			params = frags[1:]
			kw_params = extract_vars(app.request.params)

			# Execute routed method and save to output
			#
			output = getattr(app,method)(*params, **kw_params)
			if isinstance(output,unicode): 
				app.response.text  = output
			else: 
				app.response.body = output
		except Interrupt: 
			pass
		except:
			app.response.status = '500 Internal Server Error'
			app.response.body = traceback.format_exc() if DEV else 'Unknown error'
			if DEV: 
				print app.response.body
		self.flush(app.response.status, app.response.body, app.response.headers.items())

	def __iter__(self):
		self.start_response(self.response.status, self.response.headers)
		yield self.response.body

	def flush(self, status, body='', headers=[('Content-Type','text/plain')]):
		self.response.status = status
		self.response.body = body
		self.response.headers = headers

##----------------------------------------------------------------##

def run(port=8000, key=None):
	from wsgiref.simple_server import make_server
	server = make_server('', port, Twist)
	print 'serving on port', port
	server.serve_forever()

##----------------------------------------------------------------##
