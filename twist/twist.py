'''
package: twist
version: 0.2.2
author: Vinhthuy Phan
'''
import os
import re
import sys
import json
import types
import traceback
from webob import Request, Response, static
from urllib import urlencode
from urlparse import parse_qs, urljoin, urlsplit, urlunsplit
from collections import namedtuple
from jinja2 import Environment, FileSystemLoader as jj2_loader, TemplateNotFound
from .session import CookieSession
from .hook import Hook

Session = CookieSession

ViewConfig = namedtuple('ViewConfig',
	['working_directory', 'secret', 'session_timeout'])

##------------------------------------------------------------------------##
class Route (object):
	table = {'': None}
	path = {}
	view = {}

	@classmethod
	def add(cls, name, obj):
		''' Route.add('ArticleUpdate', klass) '''
		cls.view[name] = obj
		tokens = cls.split_name(name,[])
		cls.path[name] = os.path.join(*tokens)
		cls.add_tokens(tokens, obj, cls.table)

	@classmethod
	def lookup(cls, path):
		''' Route.lookup('/article/update') '''
		tokens = path.strip('/').split('/')
		return cls.lookup_tokens(tokens, cls.table)

	@classmethod
	def add_tokens(cls, tokens, obj, table):
		if tokens and tokens[0]:
			key = tokens.pop(0)
			if key not in table:
				table[key] = {'': None}
			cls.add_tokens(tokens, obj, table[key])
		else:
			table[''] = obj

	@classmethod
	def lookup_tokens(cls, tokens, table):
		if tokens and tokens[0] in table:
			key = tokens.pop(0)
			obj, params = cls.lookup_tokens(tokens, table[key])
			if obj is not None:
				return (obj, params)
			params.insert(0, key)
			return (table[''], params)
		return (table[''],tokens) if isinstance(table,dict) else (table, tokens)

	@classmethod
	def split_name(cls, name, route):
		if name=='':
			return route if route else ['']
		for i in range(1, len(name)):
			if name[i].isupper():
				break
		i = i if name[i].isupper() else i+1
		token = name[:i].lower()
		route.append(token if token!='root' else '')
		return cls.split_name(name[i:], route)

	@classmethod
	def get_template_name(cls, name):
		tokens = cls.split_name(name, [])
		return ('_'.join(tokens) or 'root') + '.html'

	@classmethod
	def show(cls):
		print 'Table: ', cls.table
		print 'View: ', cls.view
		print 'Path: ', cls.path

##------------------------------------------------------------------------##
class ViewBuilder(type):
	def __new__(cls, name, bases, dct):
		if 'client_side_target' not in dct:
			dct['client_side_target'] = None

		klass = type.__new__(cls, name, bases, dct)
		if name!='View':
			Route.add(name, klass)
			setattr(klass, '_templater_', None)
		return klass

##------------------------------------------------------------------------##
'''
	Injected class variables: _templater_
'''
class View (object):
	__metaclass__ = ViewBuilder
	_path_ = ''
	config = ViewConfig(os.getcwd(), 'thebestwaytoservewhiskey', 3600)

	def __init__(self, env):
		self.request = Request(env)
		self.response = Response()
		self.session = Session(self.request, self.response, \
			self.config.session_timeout, self.config.secret)

	@classmethod
	def setup(cls, file_name=None, secret=None, session_timeout=None):
		if file_name is None:
			working_directory = cls.config.working_directory
		else:
			working_directory = os.path.dirname(os.path.realpath(file_name))
		if secret is None:
			secret = cls.config.secret
		if session_timeout is None:
			session_timeout = cls.config.session_timeout
		cls.config = ViewConfig(working_directory, secret, session_timeout)

	def template_dir(self):
		return os.path.join(self.config.working_directory, 'template')

	def static_dir(self):
		return os.path.join(self.config.working_directory, 'static')

	def static_file(self, fname):
		file_app = static.FileApp(os.path.join(self.static_dir(),fname))
		self.response = self.request.get_response(file_app)
		raise Interrupt()

	def error(self, code, message='', interrupt=True):
	 	self.response.status = code
	 	self.response.body = message
	 	if interrupt: raise Interrupt()

	def url(self, view, *args, **kwargs):
		if type(view)==str:
			if view in Route.path:
				path = os.path.join(Route.path[view], *[str(a) for a in args])
				view = Route.view[view]
			elif view.startswith('http://') or view.startswith('https://'):
				return view
			else:
				self.error(500, 'Unknown view: ' + view)
		elif type(view)==type(View):
			path = os.path.join(Route.path[view.__name__], *[str(a) for a in args])
		else:
			self.error(500, 'redirect: url must be string or View instance')
		qs = urlencode(kwargs)
		if view.client_side_target is None:
			frag = kwargs.pop('fragment','')
		else:
			frag = 'rendered_by_client'
		return urlunsplit((self.request.scheme,self.request.host,path,qs,frag))

	def redirect(self, view, *args, **kwargs):
		self.response.location = self.url(view,*args,**kwargs)
		self.response.status = 303
		raise Interrupt()

	def render(self, **kw):
		if self._templater_ is None:
			template = Route.get_template_name(self.__class__.__name__)
			try:
				p = os.path.join(self.config.working_directory, 'template')
				if self.client_side_target is None:
					l = Environment(loader=jj2_loader(p))
					self._templater_ = l.get_template(template)
				else:
					self._templater_ = open(os.path.join(p, template)).read()
			except TemplateNotFound:
				self.error(500,'template not found: ' + template)
			except:
				self.error(500, 'Error processing ' + template)
		self.response.charset = 'utf8'
		if self.client_side_target is not None:
			self.response.content_type = 'application/json'
			t = dict(template=self._templater_,target=self.client_side_target,data=kw)
			return json.dumps(t, default=self.serializer)
		else:
			self.response.content_type = 'text/html'
			kw.update(url = self.url)
			return self._templater_.render(**kw)

	def __call__(self, *args, **kwargs):
		method = getattr(self, self.request.method.lower())
		o = method(*args, **kwargs)
		if type(o) not in (str, unicode):
			self.error(500, 'View must return str or unicode')
		self.response.text = o if type(o) is unicode else unicode(o)

	def get(self, *args, **kwargs): self.error(404, 'Unknown handler')

	def post(self, *args, **kwargs): self.error(404, 'Unknown handler')

	def put(self, *args, **kwargs): self.error(404, 'Unknown handler')

	def delete(self, *args, **kwargs): self.error(404, 'Unknown handler')

	def head(self, *args, **kwargs): self.error(404, 'Unknown handler')

	def serializer(self, obj):
		if hasattr(obj, 'isoformat'):
			return obj.isoformat()
		return obj

##------------------------------------------------------------------------##
class Twist (object):
	log = False
	mode = 'Testing'

	def __init__(self, file_name=None, secret=None, session_timeout=None):
		View.setup(file_name, secret, session_timeout)
		Hook._on_setup()

	def __del__(self):
		Hook._on_teardown()

	def __call__(self, env, start_response):
		view_cls, args = Route.lookup(env['PATH_INFO'])
		view = view_cls(env)
		kwargs = self.extract_vars(view.request.params)
		try:
			Hook._before_execute_view(view)
			view(*args, **kwargs)
			Hook._after_execute_view(view)
			view.session.save()
		except Interrupt:
			view.session.save()
		except:
			if Twist.mode == 'Testing': mesg = traceback.format_exc()
			else: mesg = HTTP_CODE[400]
			view.error(400, mesg, interrupt=False)

		start_response(view.response.status, view.response.headers.items())
		return [view.response.body]

	def extract_vars(self, form):
		d = {}
		for key, value in form.items():
			if isinstance(value,list) and len(value)==1: value = value[0]
			if not key in d: d[key] = value
			elif isinstance(d[key],list): d[key].append(value)
			else: d[key]=[d[key],value]
		return d

	#----------------------------------------------------------------------
	@classmethod
	def setup(cls, log=False, mode='Testing'):
		assert mode in ('Production', 'Testing')
		cls.log = log
		cls.mode = mode

	def run(self, host='127.0.0.1', port=8000):
		from wsgiref.simple_server import make_server
		print 'serving on port', port
		try:
			make_server(host, port, self).serve_forever()
		except KeyboardInterrupt:
			print 'stop serving...'

##------------------------------------------------------------------------##
## UTILITIES
##------------------------------------------------------------------------##

class Interrupt (Exception):
	pass

##------------------------------------------------------------------------##
HTTP_CODE = {
	400 : '400 Bad Request',
	401 : '401 Unauthorized',
	404 : '404 Not Found',
	405 : '405 Method Not Allowed',
	500 : '500 Interal Server Error',
}


