from ..hook import Hook
import sqlite3

class Sqlite ( Hook ):
	def __init__(self, dbname):
		self.dbname = dbname
		self.con = None
		self.register('SQLite: '+dbname)

	def on_setup(self):
		print 'Connecting to', self.dbname
		self.con = sqlite3.connect(self.dbname)

	def on_teardown(self):
		if self.con is not None:
			print 'Closing', self.dbname
			self.con.close()

# db = SqliteHook('storage.sqlite')
# db2 = SqliteHook('extra_storage.sqlite')
# Hook._on_setup()
# Hook._before_execute_view(10)
# Hook._after_execute_view(10)
