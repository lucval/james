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

from flask import Flask, request, jsonify

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://loan-db:loan-db@localhost/loan_db'

from loan.models import db, Loan, Payment

@app.route("/loans", methods=['POST'])
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

    # Retrieve status code
    if 'status_code' in error:
        status_code = error.status_code
    else:
        # Internal error
        app.logger.error(error)
        message = "Internal server error, please contact Group Captain Lionel Mandrake."
        status_code = 500

    # Create error response
    response = {
        'success': False,
        'error': {
            'type': error.__class__.__name__,
            'message': message
        }
    }

    return jsonify(response), status_code

@app.cli.command('initdb')
def initdb_command():
    """Initializes the database."""
    db.create_all()
    app.logger.info('Database successfully initialized')