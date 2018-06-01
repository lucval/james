#!flask/bin/python

"""
Unit tests for utilities functions in loan.models module.

Author: Luca Valtulina
Email: valtulina.luca@gmail.com
Date: 30-05-2018
Version: 0.1.0
Python Version 2.7
"""

# Utils
import jwt, unittest
from datetime import datetime, timedelta

from loan.app import app
from loan import models


class TestCase(unittest.TestCase):

	def setUp(self):
		app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://///tmp/loan-test.db'

		models.db.create_all()
		models.User(email="loan@james.test").add("loanjamestest")

	def tearDown(self):
		models.db.session.remove()
		models.db.drop_all()

class UserLoginTestCase(TestCase):

	def test_user_login_success(self):
		# Login + JWT
		jwt_token = models.User().login("loan@james.test", "loanjamestest")

		# Decode JWT
		payload = jwt.decode(jwt_token, models.JWT_SECRET, algorithms=[models.JWT_ALGORITHM])

		# Fetch user
		user = models.User.query.get(payload['user_id'])

		# Asserts
		self.assertIsNotNone(user)
		self.assertEqual(user.email, "loan@james.test")

	def test_user_login_failure(self):
		with self.assertRaises(models.BadRequest) as context:
			# wrong email
			models.User().login("fakeloan@james.test", "loanjamestest")

		self.assertEquals(context.exception.message, "User 'fakeloan@james.test' login failed")

		with self.assertRaises(models.BadRequest) as context:
			# wrong email
			models.User().login("loan@james.test", "123456")

		self.assertEquals(context.exception.message, "User 'loan@james.test' login failed")

class UserAuthenticateTestCase(TestCase):

	def test_user_authenticate_success(self):
		# Login + JWT
		jwt_token = models.User().login("loan@james.test", "loanjamestest")

		# Authenticate
		models.User().authenticate(jwt_token)

	def test_user_authenticate_invalid_token_failure(self):
		with self.assertRaises(models.BadRequest) as context:
			# Authenticate
			models.User().authenticate("thisisatesttokennotarealtokenbutitlookslikeitright")

		self.assertEquals(context.exception.message, "Token is invalid")

	def test_user_authenticate_expired_token_failure(self):
		payload = {
			'user_id': "this-is-a-test-user-id",
			'exp': datetime.utcnow() - timedelta(seconds=models.JWT_EXP_DELTA_SECONDS)
		}
		jwt_token = jwt.encode(payload, models.JWT_SECRET, models.JWT_ALGORITHM)

		with self.assertRaises(models.BadRequest) as context:
			# Authenticate
			models.User().authenticate(jwt_token)

		self.assertEquals(context.exception.message, "Token is invalid")

	def test_user_authenticate_corrupted_token_failure(self):
		payload = {
			'exp': datetime.utcnow() + timedelta(seconds=models.JWT_EXP_DELTA_SECONDS)
		}
		jwt_token = jwt.encode(payload, models.JWT_SECRET, models.JWT_ALGORITHM)

		with self.assertRaises(models.BadRequest) as context:
			# Authenticate
			models.User().authenticate(jwt_token)

		self.assertEquals(context.exception.message, "Token is corrupted")

	def test_user_authenticate_unauthorized_failure(self):
		payload = {
			'user_id': "this-is-a-test-user-id",
			'exp': datetime.utcnow() + timedelta(seconds=models.JWT_EXP_DELTA_SECONDS)
		}
		jwt_token = jwt.encode(payload, models.JWT_SECRET, models.JWT_ALGORITHM)

		with self.assertRaises(models.Unauthorized) as context:
			# Authenticate
			models.User().authenticate(jwt_token)

		self.assertEquals(context.exception.message, "User is not authorized")


if __name__ == '__main__':
	unittest.main()


