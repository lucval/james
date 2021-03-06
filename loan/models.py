#!flask/bin/python

"""
Loan database models.
(James challenge for back-end candidates)

Instructions available at:
https://github.com/CrowdProcess/backend-challenge

Author: Luca Valtulina
Email: valtulina.luca@gmail.com
Date: 30-05-2018
Version: 0.1.0
Python Version 2.7
"""

import bcrypt, jwt, math, uuid
from datetime import datetime, timedelta
from dateutil import parser, tz
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import validates
from sqlalchemy.orm.exc import NoResultFound

from loan.app import app

db = SQLAlchemy(app)

JWT_SECRET = 'secret'
JWT_ALGORITHM = 'HS256'
JWT_EXP_DELTA_SECONDS = 600

### Custom exceptions ###

class BadRequest(Exception):
    status_code = 400

class Unauthorized(Exception):
    status_code = 401

class Forbidden(Exception):
    status_code = 401

class NotFound(Exception):
    status_code = 404

class Conflict(Exception):
    status_code = 409

### Utility functions ###

def format_date(date):
    """Format a date field in a datetime aware object.

    :param date: The date input field (must conform to ISO-8601 standard format).
    :return: A datetime aware object.
    :raise BadRequest: When the provided date does not conform to ISO-8601 standard format
    """
    try:
        dt = parser.parse(date)
        if (dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None):
            # Date is naive/unaware:
            dt = dt.replace(tzinfo=tz.tzlocal())
        return dt
    except ValueError as e:
        raise BadRequest("Invalid 'date' provided, please use ISO-8601 standard")

### DB models ###

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.String(36), primary_key=True, autoincrement=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    h_password = db.Column(db.String(128), nullable=False)
    salt = db.Column(db.String(30), nullable=False)

    def __repr__(self):
        return "<User {}: {}>".format(self.id, self.email)

    @validates('email')
    def _validate_input(self, key, email):
        if email is None:
            raise BadRequest("'email' field required")

        if '@' not in email:
            raise BadRequest("Invalid email address provided")

        return email

    def login(self, email, password):
        """Login a user.

        :return: a signed JWT if user has granted access.
        :raise BadRequest: when user has no granted access.
        """
        try:
            # Lookup user
            user = db.session.query(User).filter(User.email == email).one()

            # Generate hashed password using stored salt
            h_password = bcrypt.hashpw(password.encode('utf-8'), user.salt.encode('utf-8')).decode()
            if user.h_password != h_password:
                raise NoResultFound

        except NoResultFound:
            # A NotFound will be a security offence here as we are giving away which users exist in our DB.
            raise BadRequest("User '{}' login failed".format(email))

        payload = {
            'user_id': user.id,
            'exp': datetime.utcnow() + timedelta(seconds=JWT_EXP_DELTA_SECONDS)
        }
        jwt_token = jwt.encode(payload, JWT_SECRET, JWT_ALGORITHM)

        app.logger.info("User '{}' successfully logged in".format(email))
        app.logger.debug("Token: {})".format(jwt_token))

        return jwt_token.decode('utf-8')

    def authenticate(self, jwt_token):
        """Authenticate a user by validating the provided JWT and fetching the requesting user.

        :param jwt_token: The validation JWT.
        :raise Forbidden: When no token is provided.
        :raise BadRequest: When the JWT is invalid, expired or corrupted.
        :raise Unauthorized: When user is not authorized.
        """
        if not jwt_token:
            raise Forbidden("Access denied")

        app.logger.debug("Authenticate JWT token".format(jwt_token))

        try:
            payload = jwt.decode(jwt_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        except jwt.DecodeError:
            raise BadRequest("Token is invalid")
        except jwt.ExpiredSignatureError:
            raise BadRequest("Token is expired")

        if (not payload or 'user_id' not in payload):
            raise BadRequest("Token is corrupted")

        app.logger.debug("Authenticating user '{}'".format(payload['user_id']))

        user = User.query.get(payload['user_id'])
        if not user:
           raise Unauthorized("User is not authorized")

        app.logger.info("User '{}' successfully authenticated".format(user.email))

    def add(self, password):
        """Add a user record (if not yet existing)."""

        # Generate user ID
        self.id = str(uuid.uuid4())
        self.salt = bcrypt.gensalt()
        self.h_password = bcrypt.hashpw(password.encode('utf-8'), self.salt.encode('utf-8')).decode()

        try:
            db.session.add(self)
            db.session.commit()
            app.logger.info("User '{}' successfully added".format(self.email))
        except (OperationalError, IntegrityError) as e:
            db.session.rollback()

class Loan(db.Model):
    __tablename__ = 'loans'

    id = db.Column(db.String(36), primary_key=True, autoincrement=False)
    amount = db.Column(db.Integer, nullable=False)
    term = db.Column(db.Integer, nullable=False)
    rate = db.Column(db.Float, nullable=False)
    date = db.Column(db.DateTime, nullable=False)

    def __repr__(self):
        return "<Loan {}: {}$ from {} for {} months at {} interest>".format(
            self.id, self.amount, self.date, self.term, self.rate)

    @validates('amount', 'term')
    def _validate_amount(self, key, value):
        if value is None:
            raise BadRequest("'{}' field required".format(key))

        if (not isinstance(value, int) or value <= 0):
            raise BadRequest("'{}' must be a positive integer".format(key))

        return value

    @validates('rate')
    def _validate_rate(self, key, rate):
        if rate is None:
            raise BadRequest("'rate' field required")

        if (not isinstance(rate, float) or rate <= 0 or rate > 1):
            raise BadRequest("'rate' must be a positive percentage")

        return round(rate, 2)

    @validates('date')
    def _validate_date(self, key, date):
        if date is None:
            raise BadRequest("'date' field required")

        return format_date(date)

    def get(self, loan_id):
        """Fetch a loan record.

        :param loan_id: loan unique identifier.
        :return: a loan record.
        :raise NotFound: when a loan record is not found.
        """
        loan = self.query.get(loan_id)
        if not loan:
            raise NotFound("Loan '{}' not found".format(loan_id))

        return loan

    def create(self):
        """Add a loan record.

        :raise BadRequest: when a loan record could not be created due to a database integrity or operational error.
        """
        # Generate loan ID
        self.id = str(uuid.uuid4())

        try:
            db.session.add(self)
            db.session.commit()
            app.logger.info("Loan '{}' successfully added".format(self.id))
        except (OperationalError, IntegrityError) as e:
            db.session.rollback()
            raise BadRequest("Invalid loan record provided")

    def calculate_installment(self):
        """Calculate the monthly loan payment.

        :return: the monthly loan payment.
        """
        r = self.rate / 12
        return round((r + r / (math.pow((1 + r), self.term) - 1)) * self.amount, 2)

class Payment(db.Model):
    __tablename__ = 'payments'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    date = db.Column(db.DateTime, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    payment = db.Column(db.Enum('made', 'missed'), nullable=False)
    loan_id = db.Column(db.String(36), db.ForeignKey(Loan.id))

    def __repr__(self):
        return "<Payment {} {}: {}$ on date {}>".format(self.id, self.payment, self.amount, self.date)

    @validates('date')
    def _validate_date(self, key, date):
        if date is None:
            raise BadRequest("'date' field required")

        return format_date(date)

    @validates('amount')
    def _validate_amount(self, key, amount):
        if amount is None:
            raise BadRequest("'amount' field required")

        if (not isinstance(amount, float) or amount <= 0):
            raise BadRequest("'amount' must be a positive value")

        return round(amount, 2)

    @validates('payment')
    def _validate_rate(self, key, payment):
        if payment is None:
            raise BadRequest("'payment' field required")

        if payment not in ['made', 'missed']:
            raise BadRequest("'payment' must be 'made' or 'missed'")

        return payment

    def create(self):
        """Add a payment record.

        :raise BadRequest: when payment's date is prior to loan's initial date or when a payment record could not be
        created due to a database integrity or operational error.
        """
        loan = Loan().get(self.loan_id)

        if loan.date.replace(tzinfo=tz.tzlocal()) > self.date:
            raise BadRequest("Payment cannot be executed prior to loan date")

        try:
            db.session.add(self)
            db.session.commit()
            app.logger.info("Payment for loan '{}' successfully added".format(self.loan_id))
        except (OperationalError, IntegrityError) as e:
            db.session.rollback()
            raise BadRequest("Invalid payment record provided")

    def list(self, loan_id, until_date=None, only_made=True):
        """List payments record.

        :param loan_id: Filter payments per loan.
        :param until_date: List payments until the provided date.
        :param only_made: List only made payments.
        :return: A list of payments.
        :raise BadRequest: When an invalid until_date is provided.
        """
        query = db.session.query(Payment).filter(Payment.loan_id == loan_id)

        if until_date:
            try:
                parser.parse(until_date)
            except ValueError as e:
                raise BadRequest("Invalid 'until_date' provided, please use ISO-8601 standard")

            query = query.filter(Payment.date <= until_date)


        if only_made:
            query = query.filter(Payment.payment == "made")

        return query.all()
