import re
import time
import datetime
import json
#
#--------------------------------------------------------------------
#
class BaseType(object):
	REGEX_TIME = re.compile('((?P<h>[0-9]+))([^0-9 ]+(?P<m>[0-9 ]+))?([^0-9ap ]+(?P<s>[0-9]*))?\s?((?P<d>[ap]m))?')

	def __init__(self, t):
		self.type = t

	# return value of a string v, or object of the same type as self.type
	def value(self, v):
		try:
			return self.type(v)
		except:
			raise TypeError('"%s" is invalid of type %s' % (v,self.type))

	def serialize(self, v):
		return str(v)


class DatetimeType( BaseType ):
	def __init__(self):
		super(DatetimeType, self).__init__(datetime.datetime)

	def value(self, v):
		if type(v) == datetime.datetime: return v
		(y, m, d, hh, mm, ss, t0, t1, t2) = time.strptime(v,'%Y-%m-%d %H:%M:%S')
		return datetime.datetime(y, m, d, hh, mm, ss)


class DateType( BaseType ):
	def __init__(self):
		super(DateType, self).__init__(datetime.date)

	def value(self, v):
		if type(v) == datetime.date: return v
		(y, m, d, hh, mm, ss, t0, t1, t2) = time.strptime(v,'%Y-%m-%d')
		return datetime.date(y, m, d)


class TimeType( BaseType ):
	def __init__(self):
		super(TimeType, self).__init__(datetime.time)

	def value(self, v):
		if type(v) == datetime.time: return v

		''' Formats:
			hh:mm:ss [am/pm]
			hh:mm [am/pm]
			hh [am/pm]
		'''
		value = BaseType.REGEX_TIME.match(v.lower())
		(h, m, s) = (int(value.group('h')), 0, 0)
		if value.group('m') is not None:
			m = int(value.group('m'))
		if value.group('s') is not None:
			s = int(value.group('s'))
		if value.group('d') == 'pm' and 0 < h < 12:
			h = h + 12
		return datetime.time(h,m,s)


class IntType( BaseType ):
	def __init__(self):
		super(IntType,self).__init__(int)


class LongType( BaseType ):
	def __init__(self):
		super(LongType,self).__init__(long)


class FloatType( BaseType ):
	def __init__(self):
		super(FloatType,self).__init__(float)


class BoolType( BaseType ):
	def __init__(self):
		super(BoolType,self).__init__(bool)


class VarType( BaseType ):
	def __init__(self):
		super(VarType,self).__init__(str)


class VarcharType( BaseType ):
	def __init__(self):
		super(VarcharType,self).__init__(str)


class TypeFactory(object):
	_type = dict(int=IntType, long=LongType, float=FloatType, bool=BoolType,
		var=VarType, varchar=VarcharType,
		date=DateType, time=TimeType, datetime=DatetimeType)

	@classmethod
	def get(cls, t):
		if t not in cls._type:
			raise TypeError('unknown type %s' % t)
		return cls._type[t]()

##---------------------------------------------------------------------

class InvalidField( Exception ):
    def __init__(self, error, *args, **kwargs):
        super(InvalidField, self).__init__(error, *args, **kwargs)
        self.error = error

    def __str__(self):
        return '%s.' % (self.error,)

class Field(object):
	def __init__(self, field_type, *validators, **kw):
		self.type = TypeFactory.get(field_type)
		self.default = kw.get('default', None)
		self.required = kw.get('required', False)
		self.validators = validators

	def value(self, v):
		return self.type.value(v)

	def validate(self, value):
		for validator in self.validators:
			rv = validator(value)
			if rv != True:
				return False, rv
		return True, None

	def serialize(self, value):
		return self.type.serialize(value)

class ModelMeta(type):
	class field_property(object):
		def __init__(self, name, field_obj):
			self.name = name
			self.value = field_obj.default

		def __get__(self, obj, objtype):
			return self.value if obj is not None else None

		def __set__(self, obj, value):
			self.value = obj.fields[self.name].value(value)

	def __new__(cls, name, bases, dct):
		klass = type.__new__(cls, name, bases, dct)
		setattr(klass, 'fields', {})
		for a in dct:
			if isinstance(dct[a], Field):
				klass.fields[a] = dct[a]
				setattr(klass, a, ModelMeta.field_property(a, dct[a]))
		return klass

class Model(object):
	__metaclass__ = ModelMeta

	def to_dict(self):
		return { field : getattr(self,field) for field in self.fields }

	def to_json(self):
		d = {n:f.serialize(getattr(self,n)) for n,f in self.fields.items()}
		return json.dumps(d)

	def validate(self):
		for name, field in self.fields.items():
			value = getattr(self,name)
			is_valid, error = field.validate(value)
			if not is_valid:
				raise InvalidField('%s, (%s=%s)' % (error, name, value))
		return True
