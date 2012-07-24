import re
import time
import datetime
import json
import inspect
from validator import *

#--------------------------------------------------------------------
# Types
#--------------------------------------------------------------------

class BaseType(object):
	def __init__(self, t):
		self.type = t

	# return value of a string v, or object of the same type as self.type
	def value(self, v):
		if v==None: return None
		try:
			return self.type(v)
		except:
			raise TypeError('"%s" is invalid of type %s' % (v,self.type))

	def serialize(self, v):
		return str(v)

	def __str__(self):
		return str(self.type)

class DatetimeType( BaseType ):
	def __init__(self):
		super(DatetimeType, self).__init__(datetime.datetime)

	def value(self, v):
		if v is None: return None
		if isinstance(v, datetime.datetime): return v
		if not isinstance(v, (str,unicode)):
			raise TypeError('%s not an instance of Datetime' % str(v))
		if '.' in v:
			(y, m, d, hh, mm, ss, t0, t1, t2) = time.strptime(v,'%Y-%m-%d %H:%M:%S.%f')
		else:
			(y, m, d, hh, mm, ss, t0, t1, t2) = time.strptime(v,'%Y-%m-%d %H:%M:%S')
		return datetime.datetime(y, m, d, hh, mm, ss)


class DateType( BaseType ):
	def __init__(self):
		super(DateType, self).__init__(datetime.date)

	def value(self, v):
		if v is None: return None
		if isinstance(v, datetime.date): return v
		if not isinstance(v, (str,unicode)):
			raise TypeError('%s not an instance of Date' % str(v))
		(y, m, d, hh, mm, ss, t0, t1, t2) = time.strptime(v,'%Y-%m-%d')
		return datetime.date(y, m, d)


class TimeType( BaseType ):
	REGEX_TIME = re.compile('((?P<h>[0-9]+))([^0-9 ]+(?P<m>[0-9 ]+))?([^0-9ap ]+(?P<s>[0-9]*))?\s?((?P<d>[ap]m))?')

	def __init__(self):
		super(TimeType, self).__init__(datetime.time)

	def value(self, v):
		if v is None: return None
		if isinstance(v, datetime.time): return v
		if not isinstance(v, (str,unicode)):
			raise TypeError('%s not an instance of Time' % str(v))

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
		if v is None: return None
		if v in ('True', True): return True
		if v in ('False', False): return False
		raise TypeError('%s not an instance of Boolean' % v)

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


#--------------------------------------------------------------------
# EXPRESSIONS
#--------------------------------------------------------------------

class Expression(object):
	''' Boolean expressions '''
	def __init__(self, op, *operands):
		self.op = op
		self.operands = operands

	def eval(self):
		p=[o.eval() if isinstance(o, Expression) else o for o in self.operands]
		return self.op(*p)

	def __str__(self):
		params = ', '.join([str(o) for o in self.operands])
		return '%s(%s)' % (self.op.name, params)

	def __invert__(self):
		return Expression(is_not(), self)

	def __and__(self, other):
		return Expression(is_both(), self, other)

	def __or__(self, other):
		return Expression(is_either(), self, other)

	def postgresql_token_mapping(self, thing):
		if thing in (False,True): return str(thing).upper()
		if thing is None: return 'NULL'
		return thing

	def to_sql(self):
		if self.op == None:
			return 'xxx'
		left = self.left.to_sql()
		op = self.op.sql()
		if not isinstance(self.right, Expression):
			right = self.postgresql_token_mapping(self.right)
		else:
			right = self.right.to_sql()
		format = '(%s %s %s)' if op=='OR' else '%s %s %s'
		return format % (left, op, right)


##---------------------------------------------------------------------
class CUExpression ( Expression ):
	''' Comparable unary expressions have only one operand.
		The operand is comparable, not the expression itself, which is boolean
	'''
	def __init__(self, op, value):
		super(CUExpression,self).__init__(op, value)

	def set_value(self, v):
		self.operands = [ Expression(is_value(), v, self.type) ]

	def get_value(self):
		return self.operands[0].eval()

	value = property(get_value, set_value)

	# Compare "value" of the expression, not the expression itself
	def __lt__(self, other):
		return Expression(is_lt(), self.value, other)

	def __le__(self, other):
		return Expression(is_le(), self.value, other)

	def __gt__(self, other):
		return Expression(is_gt(), self.value, other)

	def __ge__(self, other):
		return Expression(is_ge(), self.value, other)

	def __eq__(self, other):
		return Expression(is_eq(), self.value, other)

	def __ne__(self, other):
		return Expression(is_ne(), self.value, other)


class Field (CUExpression):
	def __init__(self, field_type, *validators, **kw):
		self.field_type = field_type
		self.type = TypeFactory.get(field_type)
		self.validators = validators
		self.name = None
		self.model = None
		e = Expression(is_value(), kw.get('value',None), self.type)
		super(Field,self).__init__(combine_validators(validators), e)

	def serialize(self):
		return self.type.serialize(self.value)

	def __str__(self):
		return '%s: %s' % (self.name, self.value)

	def __repr__(self):
		return '%s: %s' % (self.name, super(Field,self).__str__())

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
						value=f.value
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
		for name, field in self.fields.items():
			if field.eval() == False:
				raise InvalidField('"%s" - %s' % (field.name, field.op.error))
		return True

	def to_dict(self):
		return { name:field.value for name,field in self.fields.items() }

	def to_json(self):
		d = {name:field.serialize() for name,field in self.fields.items()}
		return json.dumps(d)

	def __str__(self):
	 	return '\n'.join(str(field) for name,field in self.fields.items())

	def __repr__(self):
	 	return '\n'.join(repr(field) for name,field in self.fields.items())
