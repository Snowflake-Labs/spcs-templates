import os
import time
from threading import Semaphore
import logging

from flask import Flask, jsonify, request, make_response

# A single process should be allowed to perform a single workload batch at a time
semaphore = Semaphore(1)


def init_logger(log_name: str):
    logger = logging.getLogger(log_name)
    logger.setLevel(logging.INFO)

    ch = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s;%(levelname)s:  %(message)s", "%Y-%m-%d %H:%M:%S")
    ch.setFormatter(formatter)

    logger.addHandler(ch)
    return logger


logger = init_logger("EmbeddingsProcessorApp")

app = Flask(__name__)

total_rows = 0


def _process_internal():
    incoming_request = request.get_json()
    logger.info(f"Received request: {incoming_request}")
    data = incoming_request['data']
    global total_rows
    total_rows += len(data)
    logger.info(f"Received data of size: {len(data)}, total size: {total_rows}")
    resp_data = [[data_row[0], data_row[1]] for data_row in data]
    time.sleep(1)
    response = {'data': resp_data}
    logger.info(f"Sending response of size: {len(response['data'])}")
    logger.info(f"Sending response: {response}")
    return jsonify(response), 200


num_success = 0
num_deny = 0


@app.post('/process')
def process():
    global num_deny
    global num_success
    num_success += 1
    logger.info(f"Received request, num_success: {num_success}")
    return _process_internal()
