from ..hook import Hook
import psycopg2

class Postgres ( Hook ):
	def __init__(self, dbname, user, password):
		self.dbname = dbname
		self.user = user
		self.password = password
		self.con = None
		self.register('Postgres: '+dbname)

	def on_setup(self):
		print 'Connecting to', self.dbname
		self.con=psycopg2.connect(database=self.dbname, user=self.user, \
			password=self.password)

	def on_teardown(self):
		if self.con is not None:
			print 'Closing', self.dbname
			self.con.close()

	def __enter__(self):
		self.cur = self.con.cursor()

	def __exit__(self, exc_type, exc_value, traceback):
		if exc_type:
			self.con.rollback()
		else:
			self.con.commit()
		self.cur.close()

# db = SqliteHook('storage.sqlite')
# db2 = SqliteHook('extra_storage.sqlite')
# Hook._on_setup()
# Hook._before_execute_view(10)
# Hook._after_execute_view(10)
