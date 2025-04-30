
from flask import Flask
from flask import request
from flask import jsonify
from flask import make_response
from flask import render_template
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from cryptography.hazmat.backends import default_backend
from datetime import timedelta, timezone, datetime
import logging
import requests
import os
import sys

SERVICE_HOST = os.getenv('SERVER_HOST', '0.0.0.0')
SERVICE_PORT = os.getenv('SERVER_PORT', 9999)
CHARACTER_NAME = os.getenv('CHARACTER_NAME', 'I')


def get_logger(logger_name):
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(
        logging.Formatter(
            '%(name)s [%(asctime)s] [%(levelname)s] %(message)s'))
    logger.addHandler(handler)
    return logger


logger = get_logger('echo-service')

app = Flask(__name__)


@app.get("/healthcheck")
def readiness_probe():
    response = make_response("I'm ready!")

    # Sending both Custom-Header-X and Custom-Header-Y but only Custom-Header-X is exposed
    response.headers['Custom-Header-X'] = 'foo'
    response.headers['Custom-Header-Y'] = 'bar'
    return response


@app.get("/get")
def get_func():
    response = make_response("GET success!")
    response.headers['Access-Control-Allow-Origin'] = 'https://b3efa44-sfengineering-prod2-snowservices-test2.snowflakecomputing.app'
    response.headers['Access-Control-Allow-Credentials'] = True
    response.headers['Access-Control-Allow-Headers'] = 'Fake-Header-X,Fake-Header-Y,Fake-Header-Z'

    # Sending both Custom-Header-X and Custom-Header-Y but only Custom-Header-X is exposed
    response.headers['Custom-Header-X'] = 'foo'
    response.headers['Custom-Header-Y'] = 'bar'
    return response


@app.route('/echo', methods=['POST'])
def echo(): 
    payload = request.get_json()

    # Making sure that Access-Control-Allow-Headers appear
    assert "Custom-Header-A" in request.headers, request.headers
    
    response = make_response(payload)

    # Sending both Custom-Header-X and Custom-Header-Y but only Custom-Header-X is exposed
    response.headers['Custom-Header-X'] = 'foo'
    response.headers['Custom-Header-Y'] = 'bar'
    return response


@app.route("/ui", methods=["GET", "POST"])
def ui():
    '''
    Main handler for providing a web UI.
    '''
    if request.method == "POST":
        # getting input in HTML form
        input_text = request.form.get("input")
        # display input and output
        return render_template("basic_ui.html",
            echo_input=input_text,
            echo_reponse=get_echo_response(input_text))

    return render_template("basic_ui.html")


@app.route('/jwt', methods=['POST'])
def handle_data():
    if request.method == 'POST':
        data = request.json
        logger.debug(f'data when calling /jwt: {data}')
        # Load the private key from the specified file.
        user = data.get("user")
        role = data.get("role")
        isPat = data.get("isPat")
        snowflake_account_url = data.get("snowflake_account_url")
        snowflake_account_hostname = snowflake_account_url[8:]
        account = snowflake_account_hostname.split('.')[0]
        logger.debug(f'Account from Snowflake Account URL: {account}')
        endpoint = data.get("endpoint")
        key = data.get("key")
        if isPat:
            snowflake_jwt = token_exchange(key, role=role, endpoint=endpoint,
                    snowflake_account_url=snowflake_account_url, isPat=isPat)
        else:
            token = JWTGenerator(account, user, key, timedelta(minutes=59),
                timedelta(minutes=54)).get_token()
            snowflake_jwt = token_exchange(token, role=role, endpoint=endpoint,
                    snowflake_account_url=snowflake_account_url, isPat=isPat)
        
        return snowflake_jwt

@app.after_request
def apply_csp(response):
    csp = (
        "default-src *; "
        "connect-src *; "
        "img-src *; "
        "script-src * 'unsafe-inline'; "
        "style-src * 'unsafe-inline';"
        "report-uri /sfc-endpoint/csp-report;"
    )
    response.headers['Content-Security-Policy'] = csp
    return response

def get_echo_response(input):
    return f'{CHARACTER_NAME} said {input}'

if __name__ == '__main__':
    app.run(host=SERVICE_HOST, port=SERVICE_PORT)
