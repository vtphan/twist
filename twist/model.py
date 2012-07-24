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
		self.field_name = None
		self.model_name = None

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

	def sql_token_mapping(self, thing):
		if thing in (False,True): return str(thing).upper()
		if thing is None: return 'NULL'
		return thing

	def to_sql(self):
		if self.op.name in ('is_eq','is_ne','is_lt','is_le','is_gt','is_ge'):
			if isinstance(self.operands[1], Expression):
				right = self.operands[1].to_sql()
			else:
				right = self.sql_token_mapping(self.operands[1])
			return '(%s %s %s)' % (self.field_name, self.op.sql_rep, right)
		if self.op.name in ('is_both', 'is_either'):
			left = self.operands[0].to_sql()
			right = self.operands[1].to_sql()
			return '(%s %s %s)' % (left, self.op.sql_rep, right)
		if self.op.name in ('is_not',):
			return '(%s %s)' % (self.op.sql_rep, self.operands[0].to_sql())
		return ''

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
	def new_expression(self, op, other):
		e = Expression(op, self.value, other)
		e.field_name = self.field_name
		e.model_name = self.model_name
		return e

	def __lt__(self, other):
		return self.new_expression(is_lt(), other)

	def __le__(self, other):
		return self.new_expression(is_le(), other)

	def __gt__(self, other):
		return self.new_expression(is_gt(), other)

	def __ge__(self, other):
		return self.new_expression(is_ge(), other)

	def __eq__(self, other):
		return self.new_expression(is_eq(), other)

	def __ne__(self, other):
		return self.new_expression(is_ne(), other)


class Field (CUExpression):
	def __init__(self, field_type, *validators, **kw):
		self.field_type = field_type
		self.type = TypeFactory.get(field_type)
		self.validators = validators
		e = Expression(is_value(), kw.get('value',None), self.type)
		super(Field,self).__init__(combine_validators(validators), e)

	def serialize(self):
		return self.type.serialize(self.value)

	def __str__(self):
		return '%s: %s' % (self.field_name, self.value)

	def __repr__(self):
		return '%s: %s' % (self.field_name, super(Field,self).__str__())

##---------------------------------------------------------------------
class field_property(object):
	def __init__(self, field_name):
		self.field_name = field_name

	def __get__(self, obj, objtype):
		if obj is not None:
			return obj.fields[self.field_name]
		else:
			return objtype._fields[self.field_name]

	def __set__(self, obj, value):
		if obj != None:
			obj.fields[self.field_name].value = value
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
				field.field_name = a
				field.model_name = name
				klass._fields[a] = field
				setattr(klass, a, field_property(a))
		return klass

class Model(object):
	__metaclass__ = ModelMeta

	def __init__(self, instance=None, db=None):
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
			field.field_name = f.field_name
			field.model_name = f.model_name
			self.fields[n] = field

		if instance:
			if isinstance(instance, dict):
				for n, v in instance.items():
					if n in self.fields:
						setattr(self, n, v)
			else:
				for n in self.fields:
					if hasattr(instance, n):
						setattr(self, n, getattr(instance, n))

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
				raise InvalidField('"%s" - %s' % (field.field_name, field.op.error))
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
