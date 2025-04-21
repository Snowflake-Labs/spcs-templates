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
import java.io.BufferedReader;
import java.io.FileReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.Reader;
import java.lang.reflect.Type;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Properties;
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

  // API endpoints
  private static final String STOCK_ENDPOINT = "/stock";
  private static final String TOP_GAINERS_ENDPOINT = "/top-gainers";
  private static final String STOCK_EXCHANGE_ENDPOINT = "/stock-exchange";

  // Global variables
  private static final String ServicePort =
      System.getenv("SERVER_PORT") != null ? System.getenv("SERVER_PORT") : "8080";

  private static final Logger logger = Logger.getLogger(StockSnapService.class.getName());
  private static Tracer tracer;
  private static LongCounter requestCounter;
  private static LongHistogram responseHistogram;
  private static ObservableLongGauge stockCountGauge;

  private static final Random random = new Random();

  public static void main(String[] args) throws Exception {
    // Create Jetty Server on port 8080
    Server server = new Server(Integer.parseInt(ServicePort));

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
    context.addServlet(
        new ServletHolder(new StockExchangeServlet(stockPrices)), STOCK_EXCHANGE_ENDPOINT);

    // Initialize OpenTelemetry and configure
    OpenTelemetry openTelemetry = Configuration.initOpenTelemetry();

    tracer = openTelemetry.getTracer("com.snowflake");
    Meter meter = openTelemetry.getMeter("com.snowflake");

    requestCounter =
        meter
            .counterBuilder("request_count")
            .setDescription("Counts the number of requests")
            .build();
    responseHistogram =
        meter
            .histogramBuilder("response_latency")
            .setDescription("Latency of responses")
            .setUnit("ms")
            .ofLongs()
            .build();
    stockCountGauge =
        meter
            .gaugeBuilder("stock_count")
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

        // Validate input
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

        // Fetch price
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

        // Fetch prices
        Span fetchPricesSpan = tracer.spanBuilder("fetch_prices").startSpan();
        List<Map.Entry<String, Double>> sortedStocks;
        try (Scope ignored1 = fetchPricesSpan.makeCurrent()) {
          randomSleep();
          sortedStocks =
              stockPrices.entrySet().stream()
                  .sorted(Collections.reverseOrder(Map.Entry.comparingByValue()))
                  .toList();
        } finally {
          fetchPricesSpan.end();
        }

        // Sort and filter prices
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
        requestCounter.add(
            1, Attributes.of(AttributeKey.stringKey("endpoint"), TOP_GAINERS_ENDPOINT));
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

  public static class StockExchangeServlet extends HttpServlet {
    private final Map<String, Double> stockPrices;

    public StockExchangeServlet(Map<String, Double> stockPrices) {
      this.stockPrices = stockPrices;
    }

    @Override
    protected void doGet(HttpServletRequest req, HttpServletResponse resp) throws IOException {
      long startTime = System.currentTimeMillis();
      Span span = tracer.spanBuilder("get_stock_exchange").startSpan();

      try (Scope ignored = span.makeCurrent()) {
        String symbol = req.getParameter("symbol");

        // Validate input
        Span validationSpan = tracer.spanBuilder("validate_input").startSpan();
        try (Scope ignored1 = validationSpan.makeCurrent()) {
          randomSleep();
          if (symbol == null || !stockPrices.containsKey(symbol)) {
            validationSpan.setStatus(io.opentelemetry.api.trace.StatusCode.ERROR, "Invalid symbol");
            resp.setStatus(HttpServletResponse.SC_BAD_REQUEST);
            JsonObject errorJson = new JsonObject();
            errorJson.addProperty("error", "Invalid symbol");
            resp.getWriter().println(new Gson().toJson(errorJson));
            logger.info("GET /stock-exchange - 400 - Invalid symbol");
            return;
          }
        } finally {
          validationSpan.end();
        }

        // Fetch exchange
        Span fetchExchangeSpan = tracer.spanBuilder("fetch_exchange").startSpan();

        try (Scope ignored1 = fetchExchangeSpan.makeCurrent()) {
          randomSleep();

          // SnowPark Container Services provide environment variables to facilitate creating a
          // connection and running queries
          String host = System.getenv("SNOWFLAKE_HOST");
          String account = System.getenv("SNOWFLAKE_ACCOUNT");
          String token = getLoginToken();
          String warehouse = System.getenv("SNOWFLAKE_WAREHOUSE");
          String database = System.getenv("SNOWFLAKE_DATABASE");
          String schema = System.getenv("SNOWFLAKE_SCHEMA");

          String table = "STOCK_EXCHANGES";
          String column = "EXCHANGE";

          // Create connection
          Connection conn = getConnection(host, account, token, warehouse, database, schema);

          // SQL query to retrieve stock exchange
          String query =
              String.format(
                  "SELECT %s FROM %s.%s.%s WHERE symbol = '%s'",
                  column, database, schema, table, symbol);

          // Execute query
          ResultSet resultSet = executeStatement(query, conn);

          boolean resultExists = resultSet.next();

          if (!resultExists) {
            validationSpan.setStatus(
                io.opentelemetry.api.trace.StatusCode.ERROR,
                "Invalid symbol for stock exchange table");
            resp.setStatus(HttpServletResponse.SC_BAD_REQUEST);

            JsonObject errorJson = new JsonObject();
            errorJson.addProperty("error", "Invalid symbol for stock exchange table");
            resp.getWriter().println(new Gson().toJson(errorJson));

            logger.info("GET /stock-exchange - 400 - Invalid symbol for stock exchange table");
            return;
          }

          // Extract exchange from query response
          String exchange = resultSet.getString(1);

          JsonObject responseJson = new JsonObject();
          responseJson.addProperty("symbol", symbol);
          responseJson.addProperty("exchange", exchange);

          // Update API response status and write response
          resp.setStatus(HttpServletResponse.SC_OK);
          resp.getWriter().println(new Gson().toJson(responseJson));
          logger.info("GET /stock-exchange - 200 - " + symbol + ": " + exchange);
        } finally {
          fetchExchangeSpan.end();
        }

        // Record metrics
        requestCounter.add(
            1, Attributes.of(AttributeKey.stringKey("endpoint"), STOCK_EXCHANGE_ENDPOINT));
        responseHistogram.record(
            System.currentTimeMillis() - startTime,
            Attributes.of(AttributeKey.stringKey("endpoint"), STOCK_EXCHANGE_ENDPOINT));

      } catch (SQLException e) {
        span.setStatus(
            io.opentelemetry.api.trace.StatusCode.ERROR, "SQL exception: " + e.getMessage());
        logger.info("GET /stock-exchange - 500 - SQL exception: " + e.getMessage());
      } catch (Exception e) {
        span.setStatus(
            io.opentelemetry.api.trace.StatusCode.ERROR, "Unhandled exception: " + e.getMessage());
        logger.severe("GET /stock-exchange - 500 - Unhandled exception: " + e.getMessage());
        throw e;
      } finally {
        span.end();
      }
    }
  }

  private static ResultSet executeStatement(String sql, Connection conn) throws SQLException {
    ResultSet resultSet = null;
    try {
      Statement statement = conn.createStatement();
      resultSet = statement.executeQuery(sql);
    } catch (SQLException e) {
      logger.info("Error executing SQL: " + sql + " " + e.getMessage());
    }
    return resultSet;
  }

  private static Connection getConnection(
      String host, String account, String token, String warehouse, String database, String schema)
      throws SQLException {
    Connection conn = null;
    Properties props = new Properties();
    String connectionURL;

    // Build connection URL for SPCS
    connectionURL = String.format("jdbc:snowflake://%s/", host);

    // Populate properties
    props.put("account", account);
    props.put("authenticator", "oauth");
    props.put("token", token);
    props.put("warehouse", warehouse);
    props.put("database", database);
    props.put("schema", schema);

    logger.info("Connection URL: " + connectionURL);

    // Connect to Snowflake
    try {
      conn = DriverManager.getConnection(connectionURL, props);
      if (conn == null) {
        logger.severe("Failed to connect to Snowflake, getConnection returned null");
      } else {
        logger.info("Successfully connected to Snowflake");
      }
    } catch (SQLException e) {
      logger.severe("Connection to Snowflake failed: " + e.getMessage());
      throw e;
    }

    // Return connection
    return conn;
  }

  private static String getLoginToken() {
    try (BufferedReader reader = new BufferedReader(new FileReader("/snowflake/session/token"))) {
      return reader.readLine();
    } catch (IOException e) {
      logger.severe("Failed to read login token: " + e.getMessage());
      return "";
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
