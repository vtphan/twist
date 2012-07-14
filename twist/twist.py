'''
package: twist
version: 0.2.2
author: Vinhthuy Phan
'''
import os
import re
import sys
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
class ViewBuilder(type):
	def __new__(cls, name, bases, dct):
		klass = type.__new__(cls, name, bases, dct)
		setattr(klass, '_route_', {'': klass})
		if name!='View':
			handle = dct.get('key', Twist.auto_path_gen(name))
			setattr(klass, 'key', handle)

			base = [b for b in bases if issubclass(b,View)]
			if len(base)>1:
				raise Exception('"%s" must derive from exactly one View'%name)
			else:
				if handle in base[0]._route_ and base[0] is not View:
					raise Exception('Duplicate handle: '+handle)
				base[0]._route_[handle] = klass
				setattr(klass, '_path_', os.path.join(base[0]._path_, handle))

			if 'template' not in dct:
				setattr(klass,'template',None)
			setattr(klass, '_templater_', None)

		return klass

##------------------------------------------------------------------------##
'''
	User-defined class variables: key, template
	Injected class variables: _route_, _path_, _templater_
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
	def setup(cls, file_loc=None, secret=None, session_timeout=None):
		if file_loc is None:
			working_directory = cls.config.working_directory
		else:
			working_directory = os.path.dirname(os.path.realpath(file_loc))
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
		file_app = static.FileApp(self.static_dir())
		self.response = self.request.get_response(file_app)
		raise Interrupt()

	def error(self, code, message='', interrupt=True):
	 	self.response.status = code
	 	self.response.body = message
	 	if interrupt: raise Interrupt()

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
		if self._templater_ is None:
			if self.template is None:
				self.error(500, 'Template not found')
			try:
				p = os.path.join(self.config.working_directory, 'template')
				l = Environment(loader=jj2_loader(p))
				self._templater_ = l.get_template(self.template)
			except TemplateNotFound:
				self.error(500,self.template+' not found or view not set up')
			except:
				self.error(500, 'Error processing '+self.template)
		self.response.content_type = 'text/html'
		self.response.charset = 'utf8'
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

##------------------------------------------------------------------------##
class Twist (object):
	log = False
	mode = 'Testing'

	def __init__(self):
		Hook._on_setup()

	def __del__(self):
		Hook._on_teardown()

	def __call__(self, env, start_response):
		tokens = env['PATH_INFO'].strip('/').split('/')
		view_cls, args = locate_view(tokens, View)
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
	def setup(cls, log=False, mode='Testing', auto_path_gen=None):
		assert mode in ('Production', 'Testing')
		cls.log = log
		cls.mode = mode
		if auto_path_gen is not None:
			cls.auto_path_gen = auto_path_gen

	def run(self, host='127.0.0.1', port=8000):
		from wsgiref.simple_server import make_server
		print 'serving on port', port
		try:
			make_server(host, port, self).serve_forever()
		except KeyboardInterrupt:
			print 'stop serving...'

	@classmethod
	def auto_path_gen(cls, name):
		''' convert camelcase names to pretty paths:
			Example:  convert_name(ArticleByMonth) -> article-by-month
		'''
		name = name.replace('_','-')
		s = re.sub('(.)([A-Z][a-z]+)', r'\1-\2', name)
		return re.sub('([a-z0-9])([A-Z])', r'\1-\2', s).lower().strip('/')

##------------------------------------------------------------------------##
## UTILITIES
##------------------------------------------------------------------------##
def locate_view(tokens, cur_view=View):
	'''
	Example: locate_view(['post','category','10'], View)
	'''
	dct = cur_view._route_
	if len(tokens)==0 or tokens[0] not in dct:
		if cur_view == dct['']:
			return (cur_view, tokens)
		return locate_view(tokens, dct[''])
	name = tokens.pop(0)
	return locate_view(tokens, dct[name])

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


