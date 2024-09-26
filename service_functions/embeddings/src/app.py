import os
import time
from threading import Semaphore

from flask import Flask, jsonify, request, make_response
from utils import init_logger, load_toml_config, get_compute_pool_type

from feature_extractor import InputRow, extract_embeddings, ModelConfiguration

# A single process should be allowed to perform a single workload batch at a time
semaphore = Semaphore(1)
semaphore_process_cpu = Semaphore(1)

logger = init_logger("EmbeddingsProcessorApp")

app = Flask(__name__)

config = load_toml_config()
model_configuration = ModelConfiguration(model_name=config['general']['model_name'],
                                         tokenizer_name=config['general']['tokenizer_name'])

batch_size = config["compute_pool"][get_compute_pool_type()]['batch_size']


def _process_internal():
    incoming_request = request.get_json()
    logger.debug(f"Received request: {incoming_request}")
    data = incoming_request['data']
    logger.info(f"Received data of size: {len(data)}")
    input_rows = [InputRow(idx=data_row[0], text=data_row[1]) for data_row in data]
    num_batches = len(input_rows) // batch_size + 1
    output_rows = []
    for i in range(num_batches):
        batch_rows = input_rows[i * batch_size:(i + 1) * batch_size]
        batch_output_rows = extract_embeddings(batch_rows, batch_size, model_configuration)
        output_rows += batch_output_rows
    response = {'data': [[row.idx, row.embeddings] for row in output_rows]}
    logger.debug(f"Sending response: {response}")
    return jsonify(response), 200


num_success = 0
num_deny = 0


@app.post('/process')
def process():
    global num_deny
    global num_success
    if not semaphore.acquire(blocking=False):
        num_deny += 1
        logger.info(f"All workers are busy, try later: {os.getpid()}, num_deny:{num_deny} ")
        response = make_response(jsonify({"error": "All workers are busy, try later"}), 429)
        response.headers['Retry-After'] = '1'
        return response
    try:
        num_success += 1
        logger.info(f"Received request, num_success: {num_success}")
        return _process_internal()
    finally:
        semaphore.release()


@app.post('/process_cpu_sleep')
def process_cpu_sleep():
    global num_deny
    global num_success
    if not semaphore_process_cpu.acquire(blocking=False):
        num_deny += 1
        logger.info(f"All workers are busy, try later: {os.getpid()}, num_deny:{num_deny} ")
        response = make_response(jsonify({"error": "All workers are busy, try later"}), 429)
        return response
    try:
        num_success += 1
        incoming_request = request.get_json()
        time.sleep(5)
        return jsonify(incoming_request), 200
    finally:
        semaphore_process_cpu.release()


num_process_failure = 0


@app.post('/process_failure')
def process_failure():
    global num_deny
    global num_process_failure
    if not semaphore_process_cpu.acquire(blocking=False):
        num_deny += 1
        logger.info(f"All workers are busy, try later: {os.getpid()}, num_deny:{num_deny} ")
        response = make_response(jsonify({"error": "All workers are busy, try later"}), 429)
        response.headers['Retry-After'] = '1'
        return response
    try:
        incoming_request = request.get_json()
        if num_success % 15000 == 0:
            return jsonify(incoming_request), 500
        num_process_failure += 1
        time.sleep(2)
        return jsonify(incoming_request), 200
    finally:
        semaphore_process_cpu.release()


@app.post('/long_processing_time')
def long_processing_time():
    global num_deny
    global num_success
    if not semaphore_process_cpu.acquire(blocking=False):
        num_deny += 1
        logger.info(f"All workers are busy, try later: {os.getpid()}, num_deny:{num_deny} ")
        response = make_response(jsonify({"error": "All workers are busy, try later"}), 429)
        response.headers['Retry-After'] = '1'
        return response
    try:
        logger.info(f"num_success: {num_success} ")
        num_success += 1
        incoming_request = request.get_json()
        time.sleep(60 * 60)
        return jsonify(incoming_request), 200
    finally:
        semaphore_process_cpu.release()
