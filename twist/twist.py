'''
package: twist
version: 0.2.1
author: Vinhthuy Phan
'''
import re
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

HTTP_CODE = {
	404 : '404 Not Found',
	405 : '405 Method Not Allowed',
	500 : '500 Interal Server Error',
}

jinja_env = Environment(loader=PackageLoader('twist', TEMPLATE_DIR))

##----------------------------------------------------------------##

class Interrupt (Exception):
	pass

def convert_name(name):
	''' convert camelcase names to pretty paths:
		Example:  convert_name(ArticleByMonth) -> article-by-month
	'''
	s = re.sub('(.)([A-Z][a-z]+)', r'\1-\2', name)
	return re.sub('([a-z0-9])([A-Z])', r'\1-\2', s).lower().strip('/')

##----------------------------------------------------------------##
class Base(type):
	def __new__(cls, name, bases, dct):
		new_class = type.__new__(cls, name, bases, dct)
		setattr(new_class, '_route_', {'': new_class})

		if name=='App':
			setattr(new_class,'_path_', '/')
		else:
			# Set route
			handle = dct.get('_alias_', convert_name(name))
			for base in bases:
				if issubclass(base, App):
					base._route_[handle] = new_class
					setattr(new_class,'_path_', os.path.join(base._path_,handle))

			# Set template
			t_file = dct.get('_template_', None)
			template = jinja_env.get_template(t_file) if t_file else None
			setattr(new_class, '_tmpl_', template)
		
		return new_class

##----------------------------------------------------------------##

class App (object):
	__metaclass__ = Base

	def __init__(self, env):
		self.request = Request(env)
		self.response = Response()

	@classmethod
	def _lookup_(self, frags):
		if len(frags)==0 or frags[0] not in self._route_:
			return (self, frags)
		name = frags.pop(0)
		return self._route_[name]._lookup_(frags)

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
		if not hasattr(self, '_tmpl_'):
			self.error(404, 'Template Not found')
		self.response.content_type = 'text/html'
		self.response.charset = 'utf-8'
		return self._tmpl_.render(**kw)

##----------------------------------------------------------------##

class Twist (object):

	def __init__(self, **config):
		pass

	def __call__(self, env, start_response):
		self.start_response = start_response
		frags = env['PATH_INFO'].strip('/').split('/')
		method = env['REQUEST_METHOD'].lower()
		try:
			cls, params = App._lookup_(frags)
			if cls.__name__ == 'App':
				return self.error(404, 'Controller not found')
			if not hasattr(cls, method):
				return self.error(405)

			app = cls(env)
			kw_params = self.extract_vars(app.request.params)
			output = getattr(app,method)(*params, **kw_params)
			if isinstance(output,unicode): 
				app.response.text  = output
			elif isinstance(output,str): 
				app.response.body = output
			else:
				return self.error(500, 'Return type of controller must be str or unicode.')
		except Interrupt: 
			pass
		except:
			return self.error(500, traceback.format_exc() if DEV else 'Unknown error')

		start_response(app.response.status, app.response.headers.items())
		return app.response.body

	#----------------------------------------------------------------------
	def error(self, code, message=''):
		self.start_response(HTTP_CODE[code], [('Content-Type','text/plain')])
		if DEV:
			print message or HTTP_CODE[code]
		return message or HTTP_CODE[code]

	#----------------------------------------------------------------------
	def extract_vars(self, form):
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

def run(port=8000, key=None):
	from wsgiref.simple_server import make_server
	server = make_server('', port, Twist())
	print 'serving on port', port
	server.serve_forever()

##----------------------------------------------------------------##
