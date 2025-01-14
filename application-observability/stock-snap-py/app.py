from flask import Flask, request, jsonify
import random
import time
import logging
import json
import os
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics._internal.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.metrics import set_meter_provider, get_meter_provider, Observation
from snowflake.telemetry.trace import SnowflakeTraceIdGenerator

SERVICE_NAME = "stock_snap_py"
# Set service host and port from environment variables or use default values
SERVICE_HOST = os.getenv('SERVER_HOST', '0.0.0.0')
SERVICE_PORT = os.getenv('SERVER_PORT', 8080)

# Initialize Flask app
app = Flask(SERVICE_NAME)

# Logger setup
logger = logging.getLogger("stock_snap_py")
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.setFormatter(logging.Formatter("%(asctime)s;%(levelname)s:  %(message)s", "%Y-%m-%d %H:%M:%S"))
logger.addHandler(ch)

# OpenTelemetry setup for tracing

# SnowflakeTraceIdGenerator generates trace IDs incorporating a timestamp component to ensure both uniqueness and traceability.
# Generated trace ID consists of a leading section derived from the timestamp and a trailing section composed of a random suffix.
# Using this generator is required for Snowflake to display traces & spans in Snowsight UI.
trace_id_generator = SnowflakeTraceIdGenerator()
tracer_provider = TracerProvider(
    resource=Resource.create({"service.name": SERVICE_NAME}),
    id_generator=trace_id_generator
)
span_processor = BatchSpanProcessor(
        span_exporter=OTLPSpanExporter(insecure=True),
        schedule_delay_millis=5000
    )
tracer_provider.add_span_processor(span_processor)
trace.set_tracer_provider(tracer_provider)
tracer = trace.get_tracer(SERVICE_NAME)

# OpenTelemetry setup for metrics
metric_exporter = OTLPMetricExporter(insecure=True)
metric_reader = PeriodicExportingMetricReader(exporter=metric_exporter, export_interval_millis=5000)
meter_provider = MeterProvider(metric_readers=[metric_reader], resource=Resource.create({"service.name": SERVICE_NAME}))
set_meter_provider(meter_provider)
meter = get_meter_provider().get_meter(SERVICE_NAME)

# Define static variables for endpoints
STOCK_ENDPOINT = "/stock"
TOP_GAINERS_ENDPOINT = "/top-gainers"

# Load stock prices from JSON file
with open('stock-snap.json') as f:
    stock_prices = json.load(f)

# Define metrics
request_counter = meter.create_counter(
    name="request_count",
    description="Counts the number of requests"
)
response_histogram = meter.create_histogram(
    name="response_latency",
    description="Response latency",
    unit="ms"
)
stock_count_gauge = meter.create_observable_gauge(
    name="stock_count",
    description="Number of stock entries",
    unit="count",
    callbacks=[lambda options: [Observation(value=len(stock_prices))]]
)

@app.route(STOCK_ENDPOINT, methods=['GET'])
def get_stock_price():
    """
    Endpoint to get the stock price for a given symbol.

    This method validates the input symbol, fetches the stock price from the loaded stock prices,
    and returns the price in JSON format.

    Returns:
        Response: JSON response containing the stock symbol and price, or an error message.
    """
    with tracer.start_as_current_span("get_stock_price") as span:
        start_time = time.time()
        symbol = request.args.get('symbol')
        
        with tracer.start_as_current_span("validate_input") as child_span:
            if not symbol or symbol not in stock_prices:
                logger.info(f"GET {STOCK_ENDPOINT} - 400 - Invalid symbol")
                response = jsonify({"error": "Invalid symbol"}), 400
                span.add_event("response", {"response": str(response)})
                return response
            random_sleep()  # Simulate validation delay

        with tracer.start_as_current_span("fetch_price") as child_span:
            random_sleep()  # Simulate fetching delay
            price = stock_prices[symbol]

        response_time = (time.time() - start_time) * 1000
        request_counter.add(1, {"endpoint": STOCK_ENDPOINT})
        response_histogram.record(response_time, {"endpoint": STOCK_ENDPOINT})

        response = jsonify({"symbol": symbol, "price": price}), 200
        span.add_event("response", {"response": str(response)})
        logger.info(f"GET {STOCK_ENDPOINT} - 200 - {symbol}: {price}")
        return response

@app.route(TOP_GAINERS_ENDPOINT, methods=['GET'])
def get_top_gainers():
    """
    Endpoint to get the top 5 stock gainers.

    This method fetches the stock prices, sorts them in descending order, and returns the top 5 gainers
    in JSON format.

    Returns:
        Response: JSON response containing the top 5 stock gainers.
    """
    with tracer.start_as_current_span("get_top_gainers") as span:
        start_time = time.time()
        
        with tracer.start_as_current_span("fetch_prices") as child_span:
            random_sleep()  # Simulate fetching delay
            sorted_stocks = sorted(stock_prices.items(), key=lambda item: item[1], reverse=True)

        with tracer.start_as_current_span("sort_and_filter") as child_span:
            random_sleep()  # Simulate sorting and filtering delay
            top_gainers = [{"symbol": symbol, "price": price} for symbol, price in sorted_stocks[:5]]

        response_time = (time.time() - start_time) * 1000
        request_counter.add(1, {"endpoint": TOP_GAINERS_ENDPOINT})
        response_histogram.record(response_time, {"endpoint": TOP_GAINERS_ENDPOINT})

        response = jsonify({"top_gainers": top_gainers}), 200
        span.add_event("response", {"response": str(response)})
        logger.info(f"GET {TOP_GAINERS_ENDPOINT} - 200 - {top_gainers}")
        return response

def random_sleep(min_time=0.1, max_time=1):
    """
    Sleep for a random duration between min_time and max_time seconds.
    """
    time.sleep(random.uniform(min_time, max_time))

if __name__ == '__main__':
    print(f"Running on host: {SERVICE_HOST}, port: {SERVICE_PORT}")
    app.run(host=SERVICE_HOST, port=SERVICE_PORT)