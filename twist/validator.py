import re


##---------------------------------------------------------------------
class Validator(object):
	def __init__(self, name, sql_rep, b):
		self.error = None
		self.name = name
		self.sql_rep = sql_rep
		# In "a op b", b is the default second operand
		self.b = b

	def eval(self, result, a, b=None):
		if result == False:
			if b!=None:
				self.error = '%s(%s, %s) = false' % (self.name, str(a), str(b))
			else:
				self.error = '%s(%s) = false' % (self.name, str(a))
		return result

class combine_validators(Validator):
	def __init__(self, validators):
		self.validators = validators
		super(combine_validators, self).__init__('combine_validators',None,None)

	def __call__(self, value):
		for validator in self.validators:
			if validator(value) == False:
				self.error = validator.error
				return False
		return True

class is_required(Validator):
	def __init__(self):
		super(is_required, self).__init__('is_required', 'NOT NULL', None)

	def __call__(self, value):
		result = value is not None
		if not result:
			self.error = 'is_required(%s) = false' % str(value)
		return result

class is_value(Validator):
	def __init__(self):
		super(is_value, self).__init__('is_value', None, None)

	def __call__(self, value, converter):
		return converter.value(value) if hasattr(converter,'value') else value

class is_eq(Validator):
	def __init__(self,b=None):
		super(is_eq, self).__init__('is_eq', '=', b)

	def __call__(self,a,b=None):
		b = b if b!=None else self.b
		return super(is_eq, self).eval(a==b, a, b)

class is_ne(Validator):
	def __init__(self,b=None):
		super(is_ne, self).__init__('is_ne', '!=', b)

	def __call__(self,a,b=None):
		b = b if b!=None else self.b
		return super(is_ne, self).eval(a!=b, a, b)

class is_lt(Validator):
	def __init__(self,b=None):
		super(is_lt, self).__init__('is_lt', '<', b)

	def __call__(self,a,b=None):
		b = b if b!=None else self.b
		return super(is_lt, self).eval(a<b, a, b)

class is_le(Validator):
	def __init__(self,b=None):
		super(is_le, self).__init__('is_le', '<=', b)

	def __call__(self,a,b=None):
		b = b if b!=None else self.b
		return super(is_le, self).eval(a<=b, a, b)

class is_gt(Validator):
	def __init__(self,b=None):
		super(is_gt, self).__init__('is_gt', '>', b)

	def __call__(self,a,b=None):
		b = b if b!=None else self.b
		return super(is_gt, self).eval(a>b, a, b)

class is_ge(Validator):
	def __init__(self,b=None):
		super(is_ge, self).__init__('is_ge', '>=', b)

	def __call__(self,a,b=None):
		b = b if b!=None else self.b
		return super(is_ge, self).eval(a>=b, a, b)

class is_both(Validator):
	def __init__(self):
		super(is_both, self).__init__('is_both', 'AND', None)

	def __call__(self,a,b):
		return super(is_both, self).eval(a and b, a, b)

class is_either(Validator):
	def __init__(self):
		super(is_either, self).__init__('is_either', 'OR', None)

	def __call__(self,a,b):
		return super(is_either, self).eval(a or b, a, b)

class is_not(Validator):
	def __init__(self):
		super(is_not, self).__init__('is_not', 'NOT', None)

	def __call__(self,a):
		return super(is_not, self).eval(not a, a, None)

class is_between(Validator):
	def __init__(self, m, n):
		self.m = m
		self.n = n
		super(is_between, self).__init__('is_between', None, None)

	def __call__(self, value):
		result = self.m <= value <= self.n
		if not result:
			self.error = 'is_between(%s, %s)(%s) = false' % \
				(str(self.m),str(self.n),str(value))
		return result

class is_length(Validator):
	def __init__(self, m, n=None):
		self.m = m
		self.n = n
		super(is_length, self).__init__('is_legnth', None, None)

	def __call__(self, value):
		if self.n==None:
			result = len(value)==self.m
			if not result:
				self.error = 'is_length(%s) != len(%s)' % (self.m, value)
		else:
			result = self.m <= len(value) <= self.n
			if not result:
				self.error = 'is_length(%s, %s) != len(%s)' % \
					(self.m, self.n, value)
		return result

class is_in(Validator):
	def __init__(self, *things):
		self.things = things
		super(is_in, self).__init__('is_in', None, None)

	def __call__(self, value):
		result = value in self.things
		if not result:
			self.error = 'is_in(%s)(%s) = false' % (str(self.things), str(value))
		return result

class is_month(is_in):
	def __init__(self):
		super(is_month, self).__init__( \
			('January','February','March','April','May','June', \
				'July','August','September','October','November','December')
		)

class is_weekday(is_in):
	def __init__(self):
		super(is_weekday, self).__init__(\
			('Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday')
		)

class is_email(Validator):
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
	def __init__(self):
		super(is_email, self).__init__('is_email', None, None)

	def __call__(self, value):
		result = True if is_email.EMAIL_REGEX.match(value) else False
		if not result:
			self.error = 'is_email(%s) = false' % str(value)
		return result

class is_url(Validator):
	URL_REGEX = re.compile(
		r'^https?://'
		r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'
		r'localhost|'
		r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
		r'(?::\d+)?'
		r'(?:/?|[/?]\S+)$', re.IGNORECASE
	)
	def __init__(self):
		super(is_url, self).__init__('is_url', None, None)

	def __call__(self):
		result = True if URL_REGEX.match(value) else False
		if not result:
			self.error = 'is_url(%s) = false' % str(value)
		return result

