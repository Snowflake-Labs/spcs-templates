package com.snowflake;

import com.google.gson.Gson;
import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import com.google.gson.reflect.TypeToken;
import com.sun.tools.javac.Main;
import io.opentelemetry.api.OpenTelemetry;
import io.opentelemetry.api.common.AttributeKey;
import io.opentelemetry.api.common.Attributes;
import io.opentelemetry.api.metrics.LongCounter;
import io.opentelemetry.api.metrics.LongHistogram;
import io.opentelemetry.api.metrics.Meter;
import io.opentelemetry.api.metrics.ObservableLongGauge;
import io.opentelemetry.api.trace.Span;
import io.opentelemetry.api.trace.Tracer;
import io.opentelemetry.context.Scope;
import jakarta.servlet.http.HttpServlet;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.Reader;
import java.lang.reflect.Type;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Random;
import java.util.logging.Logger;
import org.eclipse.jetty.server.Server;
import org.eclipse.jetty.servlet.ServletContextHandler;
import org.eclipse.jetty.servlet.ServletHolder;

/**
 * Class sets up a Jetty server to handle requests to Stock Snap service. It has two endpoints: -
 * GET /stock?symbol=<symbol> - GET /top-gainers It uses OpenTelemetry for instrumenting the code
 * with metrics, tracing and logs.
 */
public class StockSnapService {

  private static final Logger logger = Logger.getLogger(StockSnapService.class.getName());

  private static final Random random = new Random();
  private static final String STOCK_ENDPOINT = "/stock";
  private static final String TOP_GAINERS_ENDPOINT = "/top-gainers";

  private static Tracer tracer;
  private static LongCounter requestCounter;
  private static LongHistogram responseHistogram;
  private static ObservableLongGauge stockCountGauge;

  public static void main(String[] args) throws Exception {
    // Create Jetty Server on port 8080
    Server server = new Server(8080);

    // Create a ServletContextHandler for handling servlets
    ServletContextHandler context = new ServletContextHandler(ServletContextHandler.SESSIONS);
    context.setContextPath("/");
    server.setHandler(context);

    // Load stock prices from JSON file
    final Map<String, Double> stockPrices;
    Gson gson = new Gson();
    Type type = new TypeToken<HashMap<String, Double>>() {}.getType();
    try (Reader reader =
        new InputStreamReader(
            Objects.requireNonNull(
                Main.class.getClassLoader().getResourceAsStream("stock-snap.json")))) {
      stockPrices = gson.fromJson(reader, type);
    }

    // Add Servlets to handle APIs
    context.addServlet(new ServletHolder(new StockServlet(stockPrices)), STOCK_ENDPOINT);
    context.addServlet(new ServletHolder(new TopGainersServlet(stockPrices)), TOP_GAINERS_ENDPOINT);

    // Initialize OpenTelemetry and configure
    OpenTelemetry openTelemetry = Configuration.initOpenTelemetry();

    tracer = openTelemetry.getTracer("com.snowflake");
    Meter meter = openTelemetry.getMeter("com.snowflake");

    requestCounter = meter.counterBuilder("request_count")
                    .setDescription("Counts the number of requests")
                    .build();
    responseHistogram = meter.histogramBuilder("response_latency")
                    .setDescription("Latency of responses")
                    .setUnit("ms")
                    .ofLongs()
                    .build();
    stockCountGauge = meter.gaugeBuilder("stock_count")
                    .setDescription("Number of stock entries")
                    .setUnit("count")
                    .ofLongs()
                    .buildWithCallback(
                            result -> {
                              result.record(stockPrices.size(), Attributes.empty());
                            });

    // Start the server
    server.start();
    server.join();
  }

  public static class StockServlet extends HttpServlet {
    private final Map<String, Double> stockPrices;

    public StockServlet(Map<String, Double> stockPrices) {
      this.stockPrices = stockPrices;
    }

    @Override
    protected void doGet(HttpServletRequest req, HttpServletResponse resp) throws IOException {
      long startTime = System.currentTimeMillis();
      Span span = tracer.spanBuilder("get_stock_price").startSpan();

      try (Scope ignored = span.makeCurrent()) {
        String symbol = req.getParameter("symbol");

        Span validationSpan = tracer.spanBuilder("validate_input").startSpan();
        try (Scope ignored1 = validationSpan.makeCurrent()) {
          randomSleep();
          if (symbol == null || !stockPrices.containsKey(symbol)) {
            validationSpan.setStatus(io.opentelemetry.api.trace.StatusCode.ERROR, "Invalid symbol");
            resp.setStatus(HttpServletResponse.SC_BAD_REQUEST);
            JsonObject errorJson = new JsonObject();
            errorJson.addProperty("error", "Invalid symbol");
            resp.getWriter().println(new Gson().toJson(errorJson));
            logger.info("GET /stock - 400 - Invalid symbol");
            return;
          }
        } finally {
          validationSpan.end();
        }

        Span fetchPriceSpan = tracer.spanBuilder("fetch_price").startSpan();
        try (Scope ignored1 = fetchPriceSpan.makeCurrent()) {
          randomSleep();
          double price = stockPrices.get(symbol);
          JsonObject responseJson = new JsonObject();
          responseJson.addProperty("symbol", symbol);
          responseJson.addProperty("price", price);

          resp.setStatus(HttpServletResponse.SC_OK);
          resp.getWriter().println(new Gson().toJson(responseJson));
          logger.info("GET /stock - 200 - " + symbol + ": " + price);
        } finally {
          fetchPriceSpan.end();
        }

        // Record metrics
        requestCounter.add(1, Attributes.of(AttributeKey.stringKey("endpoint"), STOCK_ENDPOINT));
        responseHistogram.record(
            System.currentTimeMillis() - startTime,
            Attributes.of(AttributeKey.stringKey("endpoint"), STOCK_ENDPOINT));
      } catch (Exception e) {
        span.setStatus(
            io.opentelemetry.api.trace.StatusCode.ERROR, "Unhandled exception: " + e.getMessage());
        logger.severe("GET /stock - 500 - Unhandled exception: " + e.getMessage());
        throw e;
      } finally {
        span.end();
      }
    }
  }

  public static class TopGainersServlet extends HttpServlet {
    private final Map<String, Double> stockPrices;

    public TopGainersServlet(Map<String, Double> stockPrices) {
      this.stockPrices = stockPrices;
    }

    @Override
    protected void doGet(HttpServletRequest req, HttpServletResponse resp) throws IOException {
      long startTime = System.currentTimeMillis();
      Span span = tracer.spanBuilder("get_top_gainers").startSpan();

      try (Scope ignored = span.makeCurrent()) {
        Span fetchPricesSpan = tracer.spanBuilder("fetch_prices").startSpan();
        List<Map.Entry<String, Double>> sortedStocks;
        try (Scope ignored1 = fetchPricesSpan.makeCurrent()) {
          randomSleep();
          sortedStocks = stockPrices.entrySet().stream()
                  .sorted(Collections.reverseOrder(Map.Entry.comparingByValue()))
                  .toList();
        } finally {
          fetchPricesSpan.end();
        }

        Span sortAndFilterSpan = tracer.spanBuilder("sort_and_filter").startSpan();
        List<Map.Entry<String, Double>> topGainers;
        try (Scope ignored1 = sortAndFilterSpan.makeCurrent()) {
          randomSleep();
          topGainers = sortedStocks.stream().limit(5).toList();
        } finally {
          sortAndFilterSpan.end();
        }

        JsonArray jsonArray = new JsonArray();
        for (Map.Entry<String, Double> entry : topGainers) {
          JsonObject jsonObject = new JsonObject();
          jsonObject.addProperty("symbol", entry.getKey());
          jsonObject.addProperty("price", entry.getValue());
          jsonArray.add(jsonObject);
        }

        JsonObject responseJson = new JsonObject();
        responseJson.add("top_gainers", jsonArray);

        resp.setStatus(HttpServletResponse.SC_OK);
        resp.getWriter().println(new Gson().toJson(responseJson));
        logger.info("GET /top-gainers - 200 - " + topGainers);

        // Record metrics
        requestCounter.add(1, Attributes.of(AttributeKey.stringKey("endpoint"), TOP_GAINERS_ENDPOINT));
        responseHistogram.record(
            System.currentTimeMillis() - startTime,
            Attributes.of(AttributeKey.stringKey("endpoint"), TOP_GAINERS_ENDPOINT));
      } catch (Exception e) {
        span.setStatus(
            io.opentelemetry.api.trace.StatusCode.ERROR, "Unhandled exception: " + e.getMessage());
        logger.severe("GET /top-gainers - 500 - Unhandled exception: " + e.getMessage());
        throw e;
      } finally {
        span.end();
      }
    }
  }

  private static void randomSleep() {
    try {
      Thread.sleep(100 + random.nextInt(900)); // Random sleep between 100ms and 1s
    } catch (InterruptedException e) {
      Thread.currentThread().interrupt();
    }
  }
}
