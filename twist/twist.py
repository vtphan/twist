from webob import Request
import types

##----------------------------------------------------------------##
class route(object):
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

##----------------------------------------------------------------##
class Base(type):
    def __new__(cls, name, bases, dct):
        if name != 'app':
        	path = dct.get('__alias__', name)
        	route.set(path, type.__new__(cls, name, bases, dct))
        	return route.get(path)
        return type.__new__(cls, name, bases, dct)

##----------------------------------------------------------------##

class app(object):
	__metaclass__ = Base
	
	@classmethod
	def run(self, port=8000, key=None):
		from wsgiref.simple_server import make_server
		server = make_server('', port, self)
		print 'serving on port', port
		server.serve_forever()

	def __init__(self, env, start_response):
		frags = env['PATH_INFO'].split('/')
		if issubclass(app, type(self)):
			self.start_response = start_response
			con = route.get(frags[1])
			if con==None:
				raise Exception('controller not found for '+env.get('PATH_INFO',''))
			self._con = con(env, start_response)
			self.request = None
		else:
			self._cname = frags[1]
			self._params = frags[2:]
			self.request = Request(env)

	def __iter__(self):
		self._con._dispatch()
		self.start_response('200 OK', [('Content-type', 'text/plain')])
		yield "Hello world"

	def _dispatch(self):
		try:
			method = getattr(self, self.request.method.lower())
		except Exception as ex:
			print '> Error retrieving method:', ex
		try:
			out = method(*self._params)
		except Exception as ex:
			print '> Error executing', method, ex
		else:
			print '>', out

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
