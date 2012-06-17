'''
version: 0.2
'''

from webob import Request
import types
from urllib import urlencode
from urlparse import parse_qs

##----------------------------------------------------------------##
class Route(object):
	table = {}
	inv_table = {}

	@classmethod
	def set(self, path, cls):
		if path in self.table:
			raise Exception('route:', path, 'already exists.')
		self.table[path] = cls
		self.inv_table[cls.__name__] = path

	@classmethod
	def get(self, path):
		return self.table[path] if path in self.table else None

	@classmethod
	def inverse(self, cls_name):
		return self.inv_table[cls_name] if cls_name in inv_table else None

	@classmethod
	def show(self):
		print 'Route.table:', self.table,'\nRoute.inv_table:',self.inv_table,'\n'

##----------------------------------------------------------------##
class Base(type):
    def __new__(cls, name, bases, dct):
        if name != 'App':
        	path = dct.get('__alias__', name.lower())
        	new_class = type.__new__(cls, name, bases, dct)
        	Route.set(path, new_class)
        	Route.show()
        	return new_class
        return type.__new__(cls, name, bases, dct)

##----------------------------------------------------------------##

class App(object):
	__metaclass__ = Base

	def __init__(self, env=None):
		self.request = Request(env) if env else None

	def error(self, msg):
		pass
		
	def redirect(self, con):
		pass

	def prepare(self):
		pass

	def finish(self):
		pass

	def url(self, cls_name, *arg):
		if cls_name not in route.inverse: return ''
		pass


##----------------------------------------------------------------##

class Twist(object):
	@classmethod
	def run(self, port=8000, key=None):
		from wsgiref.simple_server import make_server
		server = make_server('', port, self)
		print 'serving on port', port
		server.serve_forever()

	def __init__(self, env, start_response):
		frags = env['PATH_INFO'].strip('/').split('/')
		self.start_response = start_response
		con = Route.get(frags[0])
		if not con:
			con = Route.get('')
			if not con:
				raise Exception('controller not found')
			self.app = con(env)
			self.params = frags
		else:
			self.app = con(env)
			self.params = frags[1:]
		if not hasattr(self.app, self.app.request.method.lower()):
			raise Exception('method not found')
		self.method = getattr(self.app, self.app.request.method.lower())
		qs_pairs = parse_qs(self.app.request.query_string).items()
		self.kw = { k:v[0] if len(v)==1 else v for k,v in qs_pairs }
		print '>qs:', self.kw

	def __iter__(self):
		self.dispatch()
		self.start_response('200 OK', [('Content-type', 'text/plain')])
		yield "Hello world"

	def dispatch(self):
		try:
			self.output = self.method(*self.params, **self.kw)
		except Exception as ex:
			print '> Error executing', self.method, ex


##----------------------------------------------------------------##

##----------------------------------------------------------------##
