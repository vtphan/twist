import bcrypt
from webob.descriptors import parse_auth, parse_auth_params

class Auth (object):
	def __init__(self, db):
		self.db = db
		with self.db:
			self.db.execute(Auth.auth_table)

	def decode_basic_auth(self, authorization):
		auth_type, auth_info = authorization
		if auth_type == 'Basic':
			username, password = auth_info.decode('base64').split(':',1)
			return username, password
		return None

	def requires_login(self, f):
		def deco(*args, **kwargs):
			view = args[0]
			if self.is_authenticated(view.session):
				return f(*args, **kwargs)
#	 		view.response.www_authenticate = 'Basic realm="Login Required"'
			return view.error(401, 'Log-in required')
		return deco

	def add_user(self, name, email, password):
		hashed = bcrypt.hashpw(password, bcrypt.gensalt())
		with self.db:
			self.db.execute("insert into auth (name,email,hashed) values \
				(%s,%s,%s)", (name, email, hashed))

	def delete_user(self, uid):
		with self.db:
			self.db.execute("delete from auth where uid=%s", (uid,))

	def update_user(self, uid, name, email, password):
		hashed = bcrypt.hashpw(password, bcrypt.gensalt())
		with self.db:
			self.db.execute("update auth set name=%s, email=%s, hashed=%s \
				where uid=%s", (name, email, hashed, uid))

	def authenticate(self, name, password):
		rv = self.db.query('select uid,hashed from auth where name=%s',(name,),1)
		if not rv:
			return -1
		uid, hashed = rv['uid'], rv['hashed']
		return uid if bcrypt.hashpw(password, hashed)==hashed else -1

	def is_authenticated(self, session):
		return 'user' in session

	def login(self, name, password, session):
		uid = self.authenticate(name, password)
		if uid < 0:
			return False
		session['user'] = uid
		return True

	def logout(self, session):
		del session['user']

	auth_table = '''create table if not exists auth (
  		uid serial primary key,
  		name varchar unique not null,
  		email varchar not null,
  		hashed varchar not null
	);'''