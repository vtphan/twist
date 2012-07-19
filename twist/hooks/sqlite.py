from ..hook import Hook
import sqlite3

class Sqlite ( Hook ):
	'''
	Declare a global variable:
		db = Sqlite('storage.sql')
	In a view (no need to play around with cursors):
		with db.con:
			db.con.execute(...)
	'''
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
