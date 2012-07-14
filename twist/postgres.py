'''
db = Postgres(database, user, password)
with db:
	db.execute(...)

'''
import psycopg2

class Postgres (object):
	def __init__(self, database, user, password, model_file=None):
		print 'Postgres: connecting to', database
		self.con=psycopg2.connect(database=database,user=user,password=password)
		self.cur = None
		if model_file:
			with open(model_file) as f:
				q = f.read()
				with self:
					self.cur.execute(q)

	def __del__(self):
		if not self.con.closed:
			print 'Postgres: closing connection'
			self.con.close()

	def __enter__(self):
		if self.con.closed:
			raise Exception('Postgres: connection is already closed.')
		self.cur = self.con.cursor()

	def __exit__(self, exc_type, exc_value, traceback):
		if exc_type: self.con.rollback()
		else: self.con.commit()
		self.cur.close()

	def execute(self, query, param=None):
		if not self.cur or self.cur.closed:
			raise Exception('Postgres: execute must inside a with statement.')
		if param:
			self.cur.execute(query, param)
		else:
			self.cur.execute(query)

	def query(self, query, args=(), size=-1):
		cur = self.con.cursor()
		cur.execute(query, args)
		rv = [dict((cur.description[idx].name, value) \
			for idx, value in enumerate(r)) for r in cur.fetchmany(size)]
		cur.close()
		return (rv[0] if rv else None) if size==1 else rv

#-----------------------------------------------------------------------
