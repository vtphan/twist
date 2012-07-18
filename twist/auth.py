import bcrypt
import inspect

class Auth (object):
	def __init__(self, db, roles=1):
		self.db = db
		self._roles = roles
		with self.db:
			self.db.execute(Auth.auth_table)

	@property
	def roles(self):
		return self._roles

	def requires_role(self, *roles):
		def function_deco(f):
			def inner_deco(*args, **kwargs):
				view = args[0]
				role = int(view.session.get('user', 0))
				if role in roles:
					return f(*args, **kwargs)
				return view.error(401, 'Role '+str(role)+' is not permitted.')

			if inspect.isfunction(f) or inspect.ismethod(f):
				return inner_deco
			elif inspect.isclass(f):
				methods = ['get','put','post','delete']
				for func in methods:
					if hasattr(f, func):
						setattr(f, func, function_deco(getattr(f,func)))
				return f
			else:
				return f

		return function_deco

	def add_user(self, name, email, password, role=1):
		hashed = bcrypt.hashpw(password, bcrypt.gensalt())
		with self.db:
			try:
				self.db.execute("insert into auth (name,email,hashed,role) values \
					(%s,%s,%s,%s)", (name, email, hashed,role))
			except: rv = False
			else: rv = True
		return rv

	def delete_user(self, name):
		with self.db:
			self.db.execute("delete from auth where name=%s", (name,))

	def update_user(self, name, email, password, role):
		hashed = bcrypt.hashpw(password, bcrypt.gensalt())
		with self.db:
			self.db.execute("update auth set email=%s, hashed=%s role=%s \
				where name=%s", (email, hashed, role, name))

	def authenticate(self, name, password):
		rv = self.db.query('select role,hashed from auth where name=%s',(name,),1)
		if not rv:
			return 0
		role, hashed = rv['role'], rv['hashed']
		return role if bcrypt.hashpw(password, hashed)==hashed else -1

	def login(self, name, password, session):
		role = self.authenticate(name, password)
		if role < 1:
			return False
		session['user'] = role
		return True

	def logout(self, session):
		del session['user']

	auth_table = '''create table if not exists auth (
  		uid serial primary key,
  		name varchar unique not null,
  		email varchar not null,
  		hashed varchar not null,
  		role int check (role > 0)
	);'''