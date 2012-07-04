from itsdangerous import URLSafeTimedSerializer, BadSignature

SESSION_COOKIE_NAME = 'twist-session'

class CookieSession(object):
	def __init__(self, request, response, max_age=360, secret='xxx'):
		self.request = request
		self.response = response
		self.max_age = max_age
		self.serializer = URLSafeTimedSerializer(secret)
		self.modified = False
		s = self.request.cookies.get(SESSION_COOKIE_NAME)
		try:
			self.session = self.serializer.loads(s) if s else {}
		except BadSignature:
			self.session = {}

	def get(self, key, default=None):
		return self.session[key] if key in self.session else default

	def __getitem__(self, key):
		return self.session[key]

	def __setitem__(self, key, value):
		self.session[key] = value
		self.modified = True

	def __delitem__(self, key):
		del self.session[key]
		self.modified = True

	def __contains__(self, key):
		return key in self.session

	def save(self):
		if not self.session:
			if self.modified:
				self.response.delete_cookie(SESSION_COOKIE_NAME,domain=domain)
			return
		self.response.set_cookie(SESSION_COOKIE_NAME,
								self.serializer.dumps(self.session),
								max_age=self.max_age,
								httponly=True)

	def __str__(self):
		return '<Session: %s>' % str(self.session)

