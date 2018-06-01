# Loan Flask application.
[James challenge for back-end candidates](https://github.com/CrowdProcess/backend-challenge)

## Prerequisite
- docker
- docker-compose

## How to run it

The project is meant to be run in a docker composition of two services:
- loan-db: MySQL database to store loan, payments and users info
- loan-app: Flask application

Before start building containers, provision the users allowed to authenticate to the application by inserting
their email and password in the users.csv file.

Now you can build the docker image firing the following command:
```bash
docker build -t james-loan:latest .
```

And start the composition with:
```bash
docker-compose up -d
```

Both containers should be running. The database is initialized and the users table is populated when 
launching the loan-app service of the composition (this means that if you want to provision other users you need
to rebuild the james-loan image and re-run the composition).
The application is now reachable at http://localhost:15000

## Login and authentication

The application has a login endpoint (http://localhost:15000/login) where users can login providing their email and
password in a JSON body as follow:
```json
{
  "email": "loan@james.test",
  "password": "supersecurepassword"
}
```
This endpoint returns a JWT token valid for the duration of 10 minutes. This JWT is required to authenticate the user
for calls to any other application's endpoint. The token is passed to the API via HTTP authorization header.
```text
Authorization: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiZWJjNGNlYzEtZDIyNy00NDk0LThhZTgtN2E0YjY0NzA4NWYyIiwiZXhwIjoxNTI3ODkwMjMwfQ.uYt9U2eXtVbp1rOnGKcmh4BMMS6Hd_ZcpUXAtAdiN8k
```

When the JWT expired a new login is required to obtain a new token.

## API

Both */loans* and */loans/<:id>/payments* endpoints are kept as [documented in the specifications](https://github.com/CrowdProcess/backend-challenge).
On the other hand the */loans/<:id>/balance* endpoint is now accepting GET only as HTTP method. The *date* input can be
specified as query parameters. An example URL is show here:
 ```text
http://localhost:15000/loans/69b73331-876b-4e80-9516-8f334c55c072/balance?until_date="2018-06-01T23:45:00+02:00"
```

## Error handling

Errors are returned in the following JSON object:
```json
{
    'error': {
        'type': <type>,
        'message': <message>
    }
}
```

## User-store security

Password are stored hashed in the user-store database together with the per-hash generated salt.

## Logs

The application is configured to log at INFO level.
Logs can be read from docker via:
```bash
docker logs -f james_loan-app_1 
```

## What is missing

- swagger/API documentation
- API model
- service layer
- configurability
- database persistence
- JWT renew/revoke capabilities
- ..

just to name a few.