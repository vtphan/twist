import re
import datetime
import json

class InvalidField( Exception ):
    def __init__(self, obj, value, error='type', *args, **kwargs):
        super(InvalidField, self).__init__(*args, **kwargs)
        self.name = obj.__class__.__name__
        self.value = value
        self.error = error

    def __str__(self):
        return '%s "%s" %s.'%(self.name, self.value, self.error)


class Field(object):
	def __init__(self, in_range=None, in_set=None, default=None, \
			required=False, multiple=False, validator=None, _type=None):
		assert isinstance(required, bool) and isinstance(multiple, bool)
		assert in_range==None or (isinstance(in_range,(tuple,list)) and len(in_range)==2)
		assert in_set==None or (isinstance(in_set,(tuple,list)))

		self.in_range = in_range
		self.in_set = in_set
		self.required = required
		self.multiple = multiple
		self.validator = validator
		self._type = _type
		if self._type == (str,unicode):
			self.range_eval = lambda x: len(x)
		else:
			self.range_eval = lambda x: x
		self.default = self.validate(default) if default is not None else None

	def validate(self, value):
		if self.required and value is None:
			raise InvalidField(self, value, 'value required')

		if self._type is not None and not isinstance(value, self._type):
			raise InvalidField(self, value, 'invalid type')

		if self.in_range!=None:
			low, high = self.in_range
			if (low is not None and self.range_eval(value) < low) or \
				(high is not None and self.range_eval(value) > high):
				raise InvalidField(self, value, 'out of range')

		if self.in_set is not None and value not in self.in_set:
			raise InvalidField(self, value, 'out of set')

		if self.validator and not self.validator(value):
			raise InvalidField(self, value, 'invalidated by custom validator')

		return value


class NumericField (Field):
	def __init__(self, in_range=None, in_set=None, default=None, \
		required=None, multiple=False, validator=None, _type=None):
		super(NumericField, self).__init__(
			in_range = in_range,
			in_set = in_set,
			default = default,
			required = required,
			multiple = multiple,
			validator = validator,
			_type = _type
		)

	def validate(self, value):
		try:
			value = self._type(value)
		except:
			raise InvalidField(self, value, 'invalid type')
		value = super(NumericField, self).validate(value)
		return value


class IntegerField (NumericField):
	def __init__(self, in_range=None,in_set=None,default=None,\
		required=False, multiple=False, validator=None):
		super(IntegerField,self).__init__(
			in_range = in_range,
			in_set = in_set,
			default = default,
			required = required,
			multiple = multiple,
			validator = validator,
			_type = int
		)

class LongField (NumericField):
	def __init__(self, in_range=None,in_set=None,default=None,\
		required=False, multiple=False, validator=None):
		super(LongField,self).__init__(
			in_range = in_range,
			in_set = in_set,
			default = default,
			required = required,
			multiple = multiple,
			validator = validator,
			_type = long
		)

class FloatField (NumericField):
	def __init__(self, in_range=None,in_set=None,default=None,\
		required=False, multiple=False, validator=None):
		super(FloatField,self).__init__(
			in_range = in_range,
			in_set = in_set,
			default = default,
			required = required,
			multiple = multiple,
			validator = validator,
			_type = float
		)

class StringField (Field):
	def __init__(self, length=None, in_set=None, default=None, \
		required=False, multiple=False, validator=None):
		super(StringField,self).__init__(
			in_range = length,
			in_set = in_set,
			default = default,
			required = required,
			multiple = multiple,
			validator = validator,
			_type = (str,unicode)
		)

class URLField (StringField):
	URL_REGEX = re.compile(
		r'^https?://'
		r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'
		r'localhost|'
		r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
		r'(?::\d+)?'
		r'(?:/?|[/?]\S+)$', re.IGNORECASE
	)

	def __init__(self, in_set=None, default=None, required=False, \
		multiple=False, validator=None):
		super(URLField,self).__init__(
			in_set = in_set,
			default = default,
			required = required,
			multiple = multiple,
			validator = validator
		)

	def validate(self, value):
		value = super(URLField, self).validate(value)
		if not URLField.URL_REGEX.match(value):
			raise InvalidField(self, value, 'invalid type')
		return value


class EmailField (StringField):
	EMAIL_REGEX = re.compile(
		# dot-atom
		r"(^[-!#$%&'*+/=?^_`{}|~0-9A-Z]+(\.[-!#$%&'*+/=?^_`{}|~0-9A-Z]+)*"
		# quoted-string
		r'|^"([\001-\010\013\014\016-\037!#-\[\]-\177]|\\[\001-011\013\014\016'
		r'-\177])*"'
		# domain
		r')@(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?$',
		re.IGNORECASE
	)

	def __init__(self, in_domain=None, in_set=None, default=None, \
		required=False, multiple=False, validator=None):
		self.in_domain = in_domain
		super(EmailField,self).__init__(
			in_set = in_set,
			default = default,
			required = required,
			multiple = multiple,
			validator = validator
		)

	def validate(self, value):
		value = super(EmailField, self).validate(value)
		if not EmailField.EMAIL_REGEX.match(value):
			raise InvalidField(self, value, 'invalid type')
		if self.in_domain!=None and value.split('@')[1] not in self.in_domain:
			raise InvalidField(self, value, 'out of range')
		return value


class MD5Field (StringField):
	def __init__(self, default=None, required=False, multiple=False, validator=None):
		super(MD5Field, self).__init__(
			length=(32,32),
			default=default,
			required=required,
			multiple = multiple,
			validator= validator
		)

	def validate(self, value):
		value = super(MD5Field, self).validate(value)
		try:
			int(value, 16)
		except:
			raise InvalidField(self, value, 'type (value is not hex)')
		return value


class SHA1Field (StringField):
	def __init__(self, default=None, required=False, multiple=False, validator=None):
		super(SHA1Field, self).__init__(
			length=(40,40),
			default=default,
			required=required,
			multiple = multiple,
			validator = validator
		)

	def validate(self, value):
		value = super(SHA1Field, self).validate(value)
		try:
			int(value, 16)
		except:
			raise InvalidField(self, value, 'type (value is not hex)')
		return value


class BooleanField (Field):
	def __init__(self, default=None, required=False, multiple=False, validator=None):
		super(BooleanField, self).__init__(
			default=default,
			required=required,
			multiple = multiple,
			valdiator = validator,
			_type = bool
		)

	def validate(self, value):
		value = super(BooleanField, self).validate(value)
		if not isinstance(value, bool):
			raise InvalidField(self, value, 'type')
		return value


class DateTimeField (Field):
	def __init__(self, in_range=None, default=None, required=False,\
		multiple=False, validator=None):
		super(DateTimeField, self).__init__(
			in_range = in_range,
			default = default,
			required = required,
			multiple = multiple,
			validator= validator,
			_type = datetime.datetime
		)

## --------------------------------------------------------------------

class ValidatorMeta (type):
	class field_property(object):
		def __init__(self, name, field_obj):
			self.name = name
			self.value = [] if field_obj.multiple else None

		def __get__(self, obj, objtype):
			return self.value if obj is not None else None

		def __set__(self, obj, value):
			field = obj.fields[self.name]
			if field.multiple:
				assert isinstance(value, list)
				_value = []
				for v in value:
					_value.append( field.validate(v) )
				self.value = _value
			else:
				self.value = obj.fields[self.name].validate(value)

	def __new__(cls, name, bases, dct):
		klass = type.__new__(cls, name, bases, dct)
		setattr(klass, 'fields', {})
		for a in dct:
			if isinstance(dct[a], Field):
				klass.fields[a] = dct[a]
				setattr(klass, a, ValidatorMeta.field_property(a, dct[a]))
		return klass


class Validator (object):
	__metaclass__ = ValidatorMeta

	def __str__(self):
		return self.fields.__str__()

	@property
	def is_valid(self):
		for name, field in self.fields.items():
			if field.required and (getattr(self,name)==None or \
				(field.multiple and getattr(self,name)==[])):
				return False
		return True
#		return not any(f.required and getattr(self,n)==None for n,f in self.fields.items())

	def to_dict(self):
		return { field : getattr(self,field) for field in self.fields }

	def to_json(self):
		return json.dumps(self.to_dict())

	@classmethod
	def form(cls):
		return ''

#---------------------------------------------------------------------
