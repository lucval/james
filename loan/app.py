#!flask/bin/python

"""
Loan Flask application.
(James challenge for back-end candidates)

Instructions available at:
https://github.com/CrowdProcess/backend-challenge

Author: Luca Valtulina
Email: valtulina.luca@gmail.com
Date: 30-05-2018
Version: 0.1.0
Python Version 2.7
"""

import csv, logging, time
from flask import Flask, request, jsonify
from functools import wraps

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://loan-db:loan-db@loan-db:3306/loan_db'
app.logger.setLevel(logging.INFO)

from loan.models import db, Loan, Payment, User, BadRequest

def authenticate(f):
    """Authentication wrapper."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        jwt_token = request.headers.get('authorization', None)
        User().authenticate(jwt_token)
        return f(*args, **kwargs)
    return decorated_function

@app.route("/login", methods=['POST'])
def login():
    """Endpoint to login to the application.

    :return: a JSON object containing the JWT to be used for further actions.
    """
    # Parse payload
    payload = request.get_json(force=True, silent=True)
    if ('email' not in payload or 'password' not in payload):
        raise BadRequest("e-mail address and password required")

    # Create JWT token
    jwt_token = User().login(payload['email'], payload['password'])

    return jsonify({"jwt_token": jwt_token}), 200

@app.route("/loans", methods=['POST'])
@authenticate
def create_loan():
    """Endpoint to create a new load record.

    :return: a JSON object containing the reference loan ID and the amount to be payed per installment.
    """
    # Parse payload
    payload = request.get_json(force=True, silent=True)

    # Create loan
    loan = Loan(**payload)
    loan.create()

    return jsonify({"loan_id": loan.id, "installment": loan.calculate_installment()}), 200

@app.route("/loans/<loan_id>/payments", methods=['POST'])
@authenticate
def create_payment(loan_id):
    """Endpoint to create a new payment record.

    :return: 204 (No Content).
    """
    # Parse payload
    payload = request.get_json(force=True, silent=True)
    payload['loan_id'] = loan_id

    # Create payment
    payment = Payment(**payload)
    payment.create()

    return '', 204

@app.route("/loans/<loan_id>/balance", methods=['GET'])
@authenticate
def fetch_balance(loan_id):
    """Retrieve outstanding debt (loan balance) at some point in time.

    :return: the volume of outstanding debt
    """
    # Fetch query parameter (would be set to None if not present)
    until_date = request.args.get("until_date")

    # Initiate outstanding balance as loan amount
    balance = Loan().get(loan_id).amount

    # Retrieve loan's payments until a specified date
    for payment in Payment().list(loan_id, until_date):
        # Adjust outstanding balance
        balance = balance - payment.amount

    return jsonify({"balance": balance}), 200

@app.errorhandler(Exception)
def handle_error(error):
    """
    Handle raised exceptions and format them in JSON error response.

    :param error: The raised error.
    :return: The proper JSON error response and status code.
    """
    # Parse message
    message = [str(x) for x in error.args]
    app.logger.error(message)

    try:
        # Retrieve status code
        status_code = error.status_code
        type = error.__class__.__name__
    except:
        # Internal error
        message = "Internal server error, please contact Group Captain Lionel Mandrake."
        status_code = 500
        type = "Internal"

    # Create error response
    response = {
        'error': {
            'type': type,
            'message': message
        }
    }

    return jsonify(response), status_code

@app.cli.command('initdb')
def initdb_command():
    """Initializes the database."""

    is_database_up = False
    for _ in range(3):
        # Three attempts before giving up
        try:
            # Initialize database
            db.create_all()
            is_database_up = True
            break
        except Exception:
            time.sleep(5)

    if not is_database_up:
        raise AssertionError("Database is not up")

    app.logger.info('Database successfully initialized')

    for row in csv.DictReader(open("/usr/local/share/users.csv", 'r')):
        User(email=row['email']).add(row['password'])
