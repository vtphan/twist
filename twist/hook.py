'''
Hook API:

def on_setup(self):
	pass

def on_teardown(self):
	pass

def before_execute_view(self, view):
	pass

def after_execute_view(self, view):
	pass
'''
class Event ( list ):
	def __init__(self, name):
		self.name = name

	def __call__(self, *args, **kwargs):
		for obj in self:
			getattr(obj, self.name)(*args, **kwargs)

	def append(self, obj):
		if hasattr(obj, self.name):
			super(Event, self).append(obj)

class Hook (object):
	names = []
	_on_setup = Event('on_setup')
	_on_teardown = Event('on_teardown')
	_before_execute_view = Event('before_execute_view')
	_after_execute_view = Event('after_execute_view')

	def register(self, name):
		Hook.names.append(name)
		Hook._on_setup.append(self)
		Hook._on_teardown.append(self)
		Hook._before_execute_view.append(self)
		Hook._after_execute_view.append(self)
