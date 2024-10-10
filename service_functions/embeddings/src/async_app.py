import asyncio
import contextlib
import http
import time
from functools import partial
from typing import AsyncIterator, cast

from starlette import concurrency
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route
from spcs_utils import init_logger, load_toml_config, get_compute_pool_type, InputRow, OutputRow, ModelConfiguration

from feature_extractor import extract_embeddings
from classifier import run_classifier

logger = init_logger("EmbeddingsProcessorApp")

_CONCURRENT_REQUESTS_MAX = 1


@contextlib.asynccontextmanager
async def lifespan(app: Starlette) -> AsyncIterator[dict]:
    app.state.model_loading_event = asyncio.Event()
    config = load_toml_config()
    app.state.max_concurrent_requests = _CONCURRENT_REQUESTS_MAX
    app.state.success_requests = 0
    app.state.throttle_requests = 0
    app.state.concurrent_requests = 0
    app.state.semaphore = asyncio.Semaphore(_CONCURRENT_REQUESTS_MAX)
    app.state.batch_size = config["compute_pool"][get_compute_pool_type()]['batch_size']
    app.state.model_configuration = ModelConfiguration(classifier_model_name=config['general']['classifier_model_name'],
                                                       embedding_model_name=config['general']['embedding_model_name'],
                                                       embedding_tokenizer_name=config['general'][
                                                           'embedding_tokenizer_name'])
    yield {}


def health(_input_json) -> JSONResponse:
    return JSONResponse({"health": "ready"}, status_code=http.HTTPStatus.OK)


def route_extract_embeddings(input_json):
    return _run_inference(input_json, extract_embeddings)


def route_classify_texts(input_json):
    return _run_inference(input_json, run_classifier)


def _run_inference(input_json, inference_function):
    data = input_json['data']
    logger.debug(f"Received request: {input_json}, size: {len(data)}")
    batch_size = app.state.batch_size
    model_configuration = app.state.model_configuration
    input_rows = [InputRow(idx=data_row[0], text=data_row[1]) for data_row in data]
    num_batches = len(input_rows) // batch_size + 1
    output_rows = []
    for i in range(num_batches):
        batch_rows = input_rows[i * batch_size:(i + 1) * batch_size]
        batch_output_rows = inference_function(batch_rows, batch_size, model_configuration)
        output_rows += batch_output_rows
    output_data = {'data': [[row.idx, row.output] for row in output_rows]}
    logger.debug(f"Sending response: {output_data}")
    return JSONResponse(content=output_data, status_code=http.HTTPStatus.OK)


def process_cpu_sleep(input_json):
    time.sleep(10)
    return JSONResponse(content=input_json, status_code=http.HTTPStatus.OK)


async def _run_with_throttling(method, request: Request) -> JSONResponse:
    app = cast(Starlette, request.app)

    if _CONCURRENT_REQUESTS_MAX:
        if app.state.concurrent_requests >= int(_CONCURRENT_REQUESTS_MAX):
            app.state.throttle_requests += 1
            logger.info(f'Number of throttled requests: {app.state.throttle_requests}')
            return JSONResponse(
                {"error": "Too many requests"}, status_code=http.HTTPStatus.TOO_MANY_REQUESTS
            )

    try:
        async with app.state.semaphore:
            app.state.success_requests += 1
            app.state.concurrent_requests += 1
            logger.info(f'Number of success requests: {app.state.success_requests}')
            input_json = await request.json()
            resp = await concurrency.run_in_threadpool(method, input_json)
            return resp
    finally:
        app.state.concurrent_requests -= 1


def _create_endpoint(method):
    async def async_method(request) -> JSONResponse:
        resp = await method(request)
        return resp

    return async_method


def run_app() -> Starlette:
    routes = [
        Route('/health', _create_endpoint(partial(_run_with_throttling, health)), methods=["GET"]),
        Route('/extract_embeddings', _create_endpoint(partial(_run_with_throttling, route_extract_embeddings)),
              methods=["POST"]),
        Route('/classify_texts', _create_endpoint(partial(_run_with_throttling, route_classify_texts)),
              methods=["POST"]),
        Route('/process_cpu_sleep', _create_endpoint(partial(_run_with_throttling, process_cpu_sleep)),
              methods=["POST"]),
    ]

    return Starlette(routes=routes, lifespan=lifespan)


app = run_app()
