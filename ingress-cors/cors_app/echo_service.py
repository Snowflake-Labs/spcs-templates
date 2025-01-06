from generateJWT import JWTGenerator

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
SERVICE_PORT = os.getenv('SERVER_PORT', 8888)
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
    return "I'm ready!"


@app.get("/get")
def get_func():
    response = make_response({"data": "GET success!"})
    response.headers['Access-Control-Allow-Origin'] = 'https://b3efa44-sfengineering-prod2-snowservices-test2.snowflakecomputing.app'
    response.headers['Access-Control-Allow-Credentials'] = True
    response.headers['Access-Control-Allow-Headers'] = 'Fake-Header-X,Fake-Header-Y,Fake-Header-Z'
    logger.debug(f'Sending response: {response.json}')
    return response


@app.route('/echo', methods=['POST'])
def echo():
    # Get the JSON payload from the request
    payload = request.get_json()
    
    # Return the payload as a JSON response
    return str(payload), 200


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

def get_p8():
    p8 = ""
    with open("./rsa_key.p8", 'rb') as pem_in:
        pemlines = pem_in.read()
        try:
            # Try to access the private key without a passphrase.
            p8 = load_pem_private_key(pemlines, None, default_backend())
            logger.debug(f"p8: {p8}")
        except TypeError:
            logger.error("Failed getting private key. ")
    return p8

def token_exchange(token, role, endpoint, snowflake_account_url):
  scope_role = f'session:role:{role}'
  scope = f'{scope_role} {endpoint}'
  data = {
    'grant_type': 'urn:ietf:params:oauth:grant-type:jwt-bearer',
    'scope': scope,
    'assertion': token,
  }
  logger.info(data)
  url = f'{snowflake_account_url}/oauth/token'
  logger.info("oauth url: %s" %url)
  response = requests.post(url, data=data, verify=False)
  logger.info("snowflake jwt : %s" % response.text)
  logger.info("response.status_code: %s" % response.status_code)
  assert 200 == response.status_code, "unable to get snowflake token"
  return response.text

@app.route('/jwt', methods=['POST'])
def handle_data():
    if request.method == 'POST':
        data = request.json
        logger.debug(f'data when calling /jwt: {data}')
        # Load the private key from the specified file.
        user = data.get("user")
        role = data.get("role")
        snowflake_account_url = data.get("snowflake_account_url")
        snowflake_account_hostname = snowflake_account_url[8:]
        account = snowflake_account_hostname.split('.')[0]
        logger.debug(f'Account from Snowflake Account URL: {account}')
        endpoint = data.get("endpoint")
        private_key_string = data.get("private_key_string")
        token = JWTGenerator(account, user, private_key_string, timedelta(minutes=59),
            timedelta(minutes=54)).get_token()
        snowflake_jwt = token_exchange(token, role=role, endpoint=endpoint,
                snowflake_account_url=snowflake_account_url)
        logger.debug(f'snowflake_jwt: {snowflake_jwt}')
        
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
