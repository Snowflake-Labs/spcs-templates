from flask import Flask
from flask import request
from flask import jsonify
from flask import make_response
from flask import render_template
from datetime import timedelta, timezone, datetime
import logging
import requests
import os
import sys

SERVICE_HOST = os.getenv('SERVER_HOST', '0.0.0.0')
SERVICE_PORT = os.getenv('SERVER_PORT', 8888)
CHARACTER_NAME = os.getenv('CHARACTER_NAME', 'I')
SNOWFLAKE_HOST = os.getenv('SNOWFLAKE_HOST')
SNOWFLAKE_ACCOUNT = os.getenv('SNOWFLAKE_ACCOUNT')


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
    response.headers['Access-Control-Allow-Origin'] = 'https://localhost:9999'
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
