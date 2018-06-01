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
import bcrypt, jwt, unittest
from datetime import datetime, timedelta

from loan.app import app
from loan.models import db, Loan, Payment, User, BadRequest, NotFound, Unauthorized, \
    JWT_SECRET, JWT_ALGORITHM, JWT_EXP_DELTA_SECONDS

test_user = {
    "email": "loan@james.test",
    "password": "loanjamestest"
}

test_loan = {
    "amount": 1000,
    "term": 12,
    "rate": 0.05,
    "date": "2018-06-01T21:44:00",
}

test_payment = {
    "payment": "made",
    "date": "2018-06-01T21:56:00",
    "amount": 85.60,
}

class TestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://///tmp/loan-test.db'
        db.create_all()

    @classmethod
    def tearDownClass(cls):
        db.session.remove()
        db.drop_all()

class UserTestCase(TestCase):

    def test_user_00_add_success(self):
        # Add user
        User(email=test_user['email']).add(test_user['password'])

        # Fetch user
        user = db.session.query(User).filter(User.email == test_user['email']).one()

        # Has password password
        h_password = bcrypt.hashpw(test_user['password'].encode('utf-8'), user.salt.encode('utf-8')).decode()

        self.assertEquals(h_password, user.h_password)

    def test_user_login_success(self):
        # Login + JWT
        jwt_token = User().login("loan@james.test", "loanjamestest")

        # Decode JWT
        payload = jwt.decode(jwt_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])

        # Fetch user
        user = User.query.get(payload['user_id'])

        # Asserts
        self.assertIsNotNone(user)
        self.assertEqual(user.email, "loan@james.test")

    def test_user_login_failure(self):
        with self.assertRaises(BadRequest) as context:
            # wrong email
            User().login("fakeloan@james.test", "loanjamestest")

        self.assertEquals(context.exception.message, "User 'fakeloan@james.test' login failed")

        with self.assertRaises(BadRequest) as context:
            # wrong email
            User().login("loan@james.test", "123456")

        self.assertEquals(context.exception.message, "User 'loan@james.test' login failed")

    def test_user_authenticate_success(self):
        # Login + JWT
        jwt_token = User().login("loan@james.test", "loanjamestest")

        # Authenticate
        User().authenticate(jwt_token)

    def test_user_authenticate_invalid_token_failure(self):
        with self.assertRaises(BadRequest) as context:
            # Authenticate
            User().authenticate("thisisatesttokennotarealtokenbutitlookslikeitright")

        self.assertEquals(context.exception.message, "Token is invalid")

    def test_user_authenticate_expired_token_failure(self):
        payload = {
            'user_id': "this-is-a-test-user-id",
            'exp': datetime.utcnow() - timedelta(seconds=JWT_EXP_DELTA_SECONDS)
        }
        jwt_token = jwt.encode(payload, JWT_SECRET, JWT_ALGORITHM)

        with self.assertRaises(BadRequest) as context:
            # Authenticate
            User().authenticate(jwt_token)

        self.assertEquals(context.exception.message, "Token is invalid")

    def test_user_authenticate_corrupted_token_failure(self):
        payload = {
            'exp': datetime.utcnow() + timedelta(seconds=JWT_EXP_DELTA_SECONDS)
        }
        jwt_token = jwt.encode(payload, JWT_SECRET, JWT_ALGORITHM)

        with self.assertRaises(BadRequest) as context:
            # Authenticate
            User().authenticate(jwt_token)

        self.assertEquals(context.exception.message, "Token is corrupted")

    def test_user_authenticate_unauthorized_failure(self):
        payload = {
            'user_id': "this-is-a-test-user-id",
            'exp': datetime.utcnow() + timedelta(seconds=JWT_EXP_DELTA_SECONDS)
        }
        jwt_token = jwt.encode(payload, JWT_SECRET, JWT_ALGORITHM)

        with self.assertRaises(Unauthorized) as context:
            # Authenticate
            User().authenticate(jwt_token)

        self.assertEquals(context.exception.message, "User is not authorized")

class LoanTestCase(TestCase):

    def test_loan_00_create_and_get_success(self):
        # Create loan
        loan = Loan(**test_loan)
        loan.create()

        test_loan['id'] = loan.id

        # Fetch loan
        db_loan = Loan().get(loan.id)

        self.assertEqual(loan, db_loan)

    def test_loan_get_failure(self):
        with self.assertRaises(NotFound) as context:
            Loan().get("this-is-a-test-loan-id")

        self.assertEquals(context.exception.message, "Loan 'this-is-a-test-loan-id' not found")

    def test_loan_create_failure(self):
        with self.assertRaises(BadRequest) as context:
            Loan().create()

        self.assertEquals(context.exception.message, "Invalid loan record provided")

    def test_calculate_installment_success(self):
        loan = Loan(**test_loan)

        self.assertEqual(loan.calculate_installment(), 85.61)

class PaymentTestCase(TestCase):

    def test_payment_00_create_success(self):
        # Create loan
        loan = Loan(**test_loan)
        loan.create()

        test_payment['loan_id'] = loan.id

        # Create payment
        payment = Payment(**test_payment)
        payment.create()

        test_payment['id'] = payment.id

        # Fetch payment
        db_payment = Payment.query.get(payment.id)

        self.assertEqual(payment, db_payment)

    def test_payment_create_past_date_failure(self):
        # Copy payment
        payment = test_payment.copy()
        payment['date'] = "2017-06-01T21:56:00"

        with self.assertRaises(BadRequest) as context:
            # Create payment
            Payment(**payment).create()

        self.assertEquals(context.exception.message, "Payment cannot be executed prior to loan date")

    def test_payment_create_past_date_failure(self):
        # Copy payment
        payment = test_payment.copy()
        del payment['amount']

        with self.assertRaises(BadRequest) as context:
            # Create payment
            Payment(**payment).create()

        self.assertEquals(context.exception.message, "Invalid payment record provided")

    def test_payment_list_success(self):
        # Pre-fetch list
        payments = Payment().list(test_payment['loan_id'])
        self.assertEqual(len(payments), 1)

        # Add a one month younger missed payment
        new_payment = test_payment.copy()
        new_payment['id'] = None
        new_payment['payment'] = "missed"
        new_payment['date'] = "2018-07-01T21:56:00"
        Payment(**new_payment).create()

        # List only made payments
        payments = Payment().list(test_payment['loan_id'])
        self.assertEqual(len(payments), 1)
        self.assertNotIn(Payment(**new_payment), payments)

        # List payments made until current month
        payments = Payment().list(test_payment['loan_id'], until_date="2018-06-01T21:56:00")
        self.assertEqual(len(payments), 1)
        self.assertNotIn(Payment(**new_payment), payments)

        # List all payments
        payments = Payment().list(test_payment['loan_id'], only_made=False)
        self.assertEqual(len(payments), 2)

if __name__ == '__main__':
    unittest.main()


