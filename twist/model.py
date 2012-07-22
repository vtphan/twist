import re
import time
import datetime
import json
import inspect
#
#--------------------------------------------------------------------
#
class BaseType(object):
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
		if '.' in v:
			(y, m, d, hh, mm, ss, t0, t1, t2) = time.strptime(v,'%Y-%m-%d %H:%M:%S.%f')
		else:
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
	REGEX_TIME = re.compile('((?P<h>[0-9]+))([^0-9 ]+(?P<m>[0-9 ]+))?([^0-9ap ]+(?P<s>[0-9]*))?\s?((?P<d>[ap]m))?')

	def __init__(self):
		super(TimeType, self).__init__(datetime.time)

	def value(self, v):
		if type(v) == datetime.time: return v

		''' Formats:
			hh:mm:ss [am/pm]
			hh:mm [am/pm]
			hh [am/pm]
		'''
		value = TimeType.REGEX_TIME.match(v.lower())
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


class BooleanType( BaseType ):
	def __init__(self):
		super(BooleanType,self).__init__(bool)

	def value(self, v):
		if v in ('True', True): return True
		if v in ('False', False): return False
		raise TypeError('invalid boolean type %s' % v)

class VarType( BaseType ):
	def __init__(self):
		super(VarType,self).__init__(str)


class VarcharType( BaseType ):
	def __init__(self):
		super(VarcharType,self).__init__(str)


class TypeFactory(object):
	_type = dict(int=IntType, long=LongType, float=FloatType,
		boolean=BooleanType, var=VarType, varchar=VarcharType,
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

##---------------------------------------------------------------------
class Field(object):
	def __init__(self, field_type, *validators, **kw):
		self.field_type = field_type
		self.validators = validators
		self.required = kw.get('required', False)
		self.value = kw.get('default', None)
		self.type = TypeFactory.get(field_type)
		self.name = None
		self.model = None

	def validate(self):
		self.value = self.type.value(self.value) if self.value!=None else None
		for validator in self.validators:
			rv = validator(self.value)
			if rv != True:
				return False, rv
		return True, None

	def serialize(self):
		return self.type.serialize(self.value)

	# def __str__(self):
	# 	return '%s: %s' % (self.name, self.value)

	# The left operand is a field; right operand is python value
	def __lt__(self, other):
		return Expression(self, '<', other)

	def __le__(self, other):
		return Expression(self, '<=', other)

	def __gt__(self, other):
		return Expression(self, '>', other)

	def __ge__(self, other):
		return Expression(self, '>=', other)

	def __eq__(self, other):
		return Expression(self, '==', other)

	def __ne__(self, other):
		return Expression(self, '!=', other)

##---------------------------------------------------------------------
class Expression(object):
	def __init__(self, left, op, right):
		self.left = left
		self.op = op
		self.right = right
		if op not in ('<','<=','>','>=','==','!=','AND','OR'):
			raise Exception('Unknown operator: ' + op)

	def __str__(self):
		return '%s %s %s' % (self.left, self.op, self.right)

	def __and__(self, other):
		return Expression(self, 'AND', other)

	def __or__(self, other):
		return Expression(self, 'OR', other)

	def postgresql_token_mapping(self, thing):
		if thing=='==': return '='
		if thing in (False,True): return str(thing).upper()
		return thing

	def to_sql(self):
		op = self.postgresql_token_mapping(self.op)
		if isinstance(self.left, Field):
			value = self.postgresql_token_mapping(self.right)
			return '%s %s %s' % (self.left.name, op, value)
		format = '(%s %s %s)' if op=='OR' else '%s %s %s'
		return format % (self.left.to_sql(), op, self.right.to_sql())

	def evaluate(self):
		if self.op == '==':
			return self.left.value == self.right
		if self.op == '!=':
			return self.left.value != self.right
		if self.op == '>':
			return self.left.value > self.right
		if self.op == '>=':
			return self.left.value >= self.right
		if self.op == '<':
			return self.left.value < self.right
		if self.op == '<=':
			return self.left.value <= self.right
		if self.op == 'AND':
			return self.left.evaluate() and self.right.evaluate()
		if self.op == 'OR':
			return self.left.evaluate() or self.right.evaluate()
		raise Exception('Unknown operator in Expression: ' + self.op)

##---------------------------------------------------------------------
class field_property(object):
	def __init__(self, name):
		self.name = name

	def __get__(self, obj, objtype):
		return obj.fields[self.name]

	def __set__(self, obj, value):
		if obj != None:
			obj.fields[self.name].value = value
		else:
			raise Exception('cannot assign value')


class ModelMeta(type):
	def __new__(cls, name, bases, dct):
		# Model._fields is a class variable
		dct['_fields'] = {}
		klass = type.__new__(cls, name, bases, dct)
		for a in dct:
			if isinstance(dct[a], Field):
				field = dct[a]
				field.name = a
				field.model = name
				klass._fields[a] = field
				setattr(klass, a, field_property(a))
		return klass

class Model(object):
	__metaclass__ = ModelMeta

	def __init__(self, db=None):
		self.db = db
		self.table_name = self.__class__.__name__

		# "fields" is an instance variable copied from class variable "_fields"
		self.fields = {}
		for n, f in self._fields.items():
			field = Field(
						f.field_type,
						*f.validators,
						required=f.required,
						default=f.value
			)
			field.name = f.name
			field.model = f.model
			self.fields[n] = field

	def _save_postgresql(self, names, values):
		sql = 'INSERT INTO %s (%s) VALUES'%(self.table_name, ', '.join(names))
		sql += ' ('+ ', '.join(['%s']*len(values)) +')'
		return sql

	# if self exists, save --> update
	def save(self):
		names = [ n for n,f in self.fields ]
		values = tuple( f.value for n,f in self.fields )
		sql = self._save_postgresql(names, values)
		if self.db != None:
			with self.db:
				db.execute(sql, values)
		else:
			print sql, values

	@classmethod
	def update(self, expr):
		pass

	@classmethod
	def find(self, expr):
		pass

	def validate(self):
		# self.fields= [p for p in inspect.getmembers(self) if isinstance(p[1],Field)]
		for name, field in self.fields.items():
			is_valid, error = field.validate()
			if not is_valid:
				raise InvalidField('%s, (%s=%s)' % (error, name, field.value))
		return True

	def to_dict(self):
		return { name:field.value for name,field in self.fields.items() }

	def to_json(self):
		d = {name:field.serialize() for name,field in self.fields.items()}
		return json.dumps(d)

	# def __str__(self):
	# 	return '{'+', '.join(i[1].__str__() for i in self.fields)+'}'
