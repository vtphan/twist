'''
package: twist
version: 0.2.2
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
from urlparse import parse_qs, urljoin, urlsplit, urlunsplit
from jinja2 import Environment, PackageLoader

LOGGING = True
DEV = True
APP_DIR = '.'
TEMPLATE_DIR = './template'
STATIC_DIR = './static'

HTTP_CODE = {
	400 : '400 Bad Request',
	404 : '404 Not Found',
	405 : '405 Method Not Allowed',
	500 : '500 Interal Server Error',
}

jinja_env = Environment(loader=PackageLoader('twist', TEMPLATE_DIR))

##------------------------------------------------------------------------##
class UnknownHandler (Exception):
	def __init__(self, code, message=''):
		self.code = code
		self.message = message

	def __str__(self):
		return self.message

##------------------------------------------------------------------------##
class Interrupt (Exception):
	pass

##------------------------------------------------------------------------##

class ViewBuilder(type):
	def __new__(cls, name, bases, dct):
		new_class = type.__new__(cls, name, bases, dct)
		new_class._route_ = {'': new_class}
		if name!='View':
			# Set route in base class
			new_class._alias_ = handle = dct.get('_alias_', convert_name(name))
			if handle=='' and all(b.__name__!='View' for b in bases):
				raise Exception('Empty _alias_ class must be subclass of View')

			base = [b for b in bases if issubclass(b,View)]
			if len(base)>1:
				raise Exception('"%s" must derive from exactly one View'%name)
			else:
				if handle in base[0]._route_ and base[0] is not View:
					raise Exception('Duplicate handle: '+handle)
				base[0]._route_[handle] = new_class
				new_class._path_ = os.path.join(base[0]._path_, handle)

			# Set template
			t = dct.get('_template_', None)
			new_class._tmpl_ = jinja_env.get_template(t) if t else None

		return new_class

##------------------------------------------------------------------------##
'''
	User-defined special variables:
		_alias_
		_template_
	Hidden special variables:
		_route_
		_path_
		_tmpl_
'''
class View (object):
	__metaclass__ = ViewBuilder
	_path_ = ''

	def __init__(self, env):
		self.request = Request(env)
		self.response = Response()

	def static_file(self, filename):
		file_app = static.FileApp(os.path.join(STATIC_DIR, filename))
		self.response = self.request.get_response(file_app)
		raise Interrupt()

	def error(self, code, message=''):
	 	self.response.status = code
	 	self.response.body = message
	 	raise Interrupt()

	def url(self, view, *args, **kwargs):
		if type(view)==str:
			if view.startswith('http://') or view.startswith('https://'):
				return view
			path = view
		elif type(view)==type(View):
			path = os.path.join(view._path_, *[str(a) for a in args])
		else:
			self.error(500, 'redirect: url must be string or View instance')
		qs = urlencode(kwargs)
		frag = kwargs.pop('fragment','')
		return urlunsplit((self.request.scheme,self.request.host,path,qs,frag))

	def redirect(self, view, *args, **kwargs):
		self.response.location = self.url(view,*args,**kwargs)
		self.response.status = 303
		raise Interrupt()

	def render(self, **kw):
		if not hasattr(self, '_tmpl_'):
			self.error(404, 'Template Not found')
		self.response.content_type = 'text/html'
		self.response.charset = 'utf-8'
		return self._tmpl_.render(**kw)

	@classmethod
	def get(cls, *args, **kwargs): raise UnknownHandler(404)

	@classmethod
	def post(cls, *args, **kwargs): raise UnknownHandler(404)

	@classmethod
	def put(cls, *args, **kwargs): raise UnknownHandler(404)

	@classmethod
	def delete(cls, *args, **kwargs): raise UnknownHandler(404)

	@classmethod
	def head(cls, *args, **kwargs): raise UnknownHandler(404)

##------------------------------------------------------------------------##
class App (object):

	def __init__(self, root=View, **config):
		self.root = root

	def __call__(self, env, start_response):
		self.start_response = start_response
		try:
			tokens = env['PATH_INFO'].strip('/').split('/')
			view, args = locate_view(tokens, self.root)
			view = view(env)
			kw_args = extract_vars(view.request.params)
			rv = getattr(view,view.request.method.lower())(*args, **kw_args)
			if isinstance(rv,unicode):
				view.response.text  = rv
			elif isinstance(rv,str):
				view.response.body = rv
			else:
				return self.error(500, 'View must return str or unicode')
		except Interrupt:
			pass
		except UnknownHandler as ex:
			return self.error(ex.code, ex.message)
		except:
			return self.error(400, traceback.format_exc() if DEV else HTTP_CODE[400])

		start_response(view.response.status, view.response.headers.items())
		return view.response.body

	#----------------------------------------------------------------------
	def error(self, code, message=''):
		self.start_response(HTTP_CODE[code], [('Content-Type','text/plain')])
		if DEV:
			print message or HTTP_CODE[code]
		return message or HTTP_CODE[code]

	def run(self, host='', port=8000):
		from wsgiref.simple_server import make_server
		print 'serving on port', port
		make_server(host, port, self).serve_forever()

##------------------------------------------------------------------------##
## UTILITIES
##------------------------------------------------------------------------##
def locate_view(tokens, cur_view=View):
	'''
	Example: locate_view(['post','category','10'], View)
	'''
	dct = cur_view._route_
	if len(tokens)==0:
		if cur_view.__name__ == dct[''].__name__:
			return (cur_view, [])
		return locate_view([], dct[''])
	if tokens[0] not in dct:
		return (cur_view, tokens)
	name = tokens.pop(0)
	return locate_view(tokens, dct[name])

##------------------------------------------------------------------------##
def convert_name(name):
	''' convert camelcase names to pretty paths:
		Example:  convert_name(ArticleByMonth) -> article-by-month
	'''
	s = re.sub('(.)([A-Z][a-z]+)', r'\1-\2', name)
	return re.sub('([a-z0-9])([A-Z])', r'\1-\2', s).lower().strip('/')

##------------------------------------------------------------------------##
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
##------------------------------------------------------------------------##


