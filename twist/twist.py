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

Session = CookieSession

ViewConfig = namedtuple('ViewConfig',
	['working_directory', 'secret', 'session_timeout'])

##------------------------------------------------------------------------##
class ViewBuilder(type):
	def __new__(cls, name, bases, dct):
		klass = type.__new__(cls, name, bases, dct)
		setattr(klass, '_route_', {'': klass})
		if name!='View':
			handle = dct.get('_alias_', Twist.auto_path_gen(name))
			setattr(klass, '_alias_', handle)
			if handle=='' and all(b.__name__!='View' for b in bases):
				raise Exception('Empty _alias_ class must be subclass of View')

			base = [b for b in bases if issubclass(b,View)]
			if len(base)>1:
				raise Exception('"%s" must derive from exactly one View'%name)
			else:
				if handle in base[0]._route_ and base[0] is not View:
					raise Exception('Duplicate handle: '+handle)
				base[0]._route_[handle] = klass
				setattr(klass, '_path_', os.path.join(base[0]._path_, handle))

			if '_template_' not in dct:
				setattr(klass,'_template_',None)
			setattr(klass, '_templater_', None)

		return klass

##------------------------------------------------------------------------##
'''
	User-defined class variables: _alias_, _template_
	Injected class variables: _route_, _path_, _templater_
'''
class View (object):
	__metaclass__ = ViewBuilder
	_path_ = ''
	config = ViewConfig(os.getcwd(), 'thebestwaytoservewhiskey', 3600)

	def __init__(self, env):
		self.request = Request(env)
		self.response = Response()
		self.args = None
		self.kw_args = None
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
		# for k,v in cls._route_.items():
		# 	if not issubclass(cls, v):
		# 		v.setup(file_loc, secret, session_timeout)

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
			if self._template_ is None:
				self.error(500, 'Template not found')
			try:
				p = os.path.join(self.config.working_directory, 'template')
				l = Environment(loader=jj2_loader(p))
				self._templater_ = l.get_template(self._template_)
			except TemplateNotFound:
				self.error(500,self._template_+' not found or view not set up')
			except:
				self.error(500, 'Error processing '+self._template_)
		self.response.content_type = 'text/html'
		self.response.charset = 'utf8'
		return self._templater_.render(**kw)

	def exec_view(self):
		method = getattr(self, self.request.method.lower())
		o = method(*self.args, **self.kw_args)
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
	mode = 'Debug'

	@classmethod
	def setup(cls, log=False, mode='Debug', auto_path_gen=None):
		cls.log = log
		cls.mode = mode
		if auto_path_gen is not None:
			cls.auto_path_gen = auto_path_gen

	def __init__(self, env, start_response):
		self.env = env
		self.start_response = start_response

	def __iter__(self):
		tokens = self.env['PATH_INFO'].strip('/').split('/')
		view_cls, left_over_tokens = locate_view(tokens, View)
		view = view_cls(self.env)
		view.args = left_over_tokens
		view.kw_args = extract_vars(view.request.params)
		try:
			view.exec_view()
			view.session.save()
		except Interrupt:
			pass
		except:
			if Twist.mode == 'Debug': mesg = traceback.format_exc()
			else: mesg = HTTP_CODE[400]
			view.error(400, mesg, interrupt=False)

		self.start_response(view.response.status, view.response.headers.items())
		yield view.response.body

	#----------------------------------------------------------------------
	@classmethod
	def run(cls, host='127.0.0.1', port=8000):
		from wsgiref.simple_server import make_server
		print 'serving on port', port
		make_server(host, port, cls).serve_forever()

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
	if len(tokens)==0:
		if cur_view.__name__ == dct[''].__name__:
			return (cur_view, [])
		return locate_view([], dct[''])
	if tokens[0] not in dct:
		return (cur_view, tokens)
	name = tokens.pop(0)
	return locate_view(tokens, dct[name])

##------------------------------------------------------------------------##
def extract_vars(form):
	d = {}
	for key, value in form.items():
		if isinstance(value,list) and len(value)==1: value = value[0]
		if not key in d: d[key] = value
		elif isinstance(d[key],list): d[key].append(value)
		else: d[key]=[d[key],value]
	return d

##------------------------------------------------------------------------##
class Interrupt (Exception):
	pass

##------------------------------------------------------------------------##
HTTP_CODE = {
	400 : '400 Bad Request',
	404 : '404 Not Found',
	405 : '405 Method Not Allowed',
	500 : '500 Interal Server Error',
}


