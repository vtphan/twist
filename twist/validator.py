import re
#
# Built-in validators
# a validator return True or an error message (if fail)
#
def is_required(value=None):
	return True if value!=None else 'a value is required'

def is_equal(n):
	return lambda value: True if n==value else '%s != %s' % (str(n),str(value))

def is_length(n):
	return lambda value: True if len(value)==n else \
		'len(%s) < %s' % (str(value),str(n))

def is_length_between(m,n):
	return lambda value: True if m <= len(value) <= n else \
		'len(%s) < %s or len(%s) > %s' % (str(value),str(m),str(value),str(n))

def is_length_atmost(n):
	return lambda value: True if len(value) <= n else 'length > %s' % str(n)

def is_between(m,n):
	return lambda value: True if m <= value <= n else \
		'%s < %s or %s > %s' % (str(value),str(m),str(value),str(n))

def is_atmost(n):
	return lambda value: True if value <= n else '%s > %s' % (str(value),str(n))

def is_atleast(n):
	return lambda value: True if value >= n else '%s < %s' % (str(value),str(n))

def is_in(*things):
	return lambda value: True if value in things else \
		'%s not in %s' % (str(value), str(things))

def is_email(value):
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
	return True if EMAIL_REGEX.match(value) else '%s is an invalid email'%str(value)

def is_url(value):
	URL_REGEX = re.compile(
		r'^https?://'
		r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'
		r'localhost|'
		r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
		r'(?::\d+)?'
		r'(?:/?|[/?]\S+)$', re.IGNORECASE
	)
	return True if URL_REGEX.match(value) else '%s is an invalid URL' % str(value)

def is_numeric(value):
	return True if isinstance(value, (int, long, float)) else \
		'%s not a numeric' % str(value)

def is_int(value):
	return True if isinstance(value,int) else '%s not an int' % str(value)

def is_long(value):
	return True if isinstance(value,long) else '%s not a long' % str(value)

def is_float(value):
	return True if isinstance(value,float) else '%s not a float' % str(value)

def is_bool(value):
	return True if isinstance(value,bool) else '%s not a bool' % str(value)

def is_str(value):
	return True if isinstance(value,str) else '%s not a str' % str(value)

def is_unicode(value):
	return True if isinstance(value,unicode) else '%s not a unicode' % str(value)

def is_month(value):
	return True if value.lower() in ('january','february','march','april',\
		'may','june','july','august','september','october','november',\
		'december') else '%s invalid month' % str(value)

def is_weekday(value):
	return True if value.lower() in ('monday','tuesday','wednesday','thursday',\
		'friday','saturday','sunday') else '%s invalid weekday' % str(value)