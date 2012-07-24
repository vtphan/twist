from model import *
from validator import *
import datetime

class Employee (Model):
	name = 			Field('var', is_length(10))
	age = 			Field('int', is_required(), is_between(17,35))
	salary = 		Field('float', is_between(10000,100000), value=20000)
	race = 			Field('varchar', is_in('Asian', 'Caucasian', 'African'))
	date_hired = 	Field('date', is_required())
	last_meeting = 	Field('datetime')
	status = 		Field('boolean', value=False)

e = Employee()
e.name = 'John Smith'
e.age = 28
e.race = 'Asian'
e.date_hired = '2013-02-13'
e.last_meeting = '2012-07-20 11:52:27'
print e.validate(), e.to_json()
#
f = Employee()
f.age = '25'
f.name = 'John Smith'
f.race = 'Caucasian'
f.date_hired = datetime.date.today()

print ((f.age < 50) & (f.race == 'Caucasian')).eval()

print ((Employee.age < 10) | ~(Employee.name=='John Smith') & (Employee.race != 'Asian')).to_sql()


g = Employee(dict(name='Mary J Bil', age='21', race='African', date_hired='2010-02-20'))
print g.to_json()
print g.validate()

class A (object):
	def __init__(self, age, name, race):
		self.age = age
		self.name = name
		self.race = race

instance = A('16', 'John Smith', 'White')
h = Employee(instance)
print h.validate()