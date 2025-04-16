package main

import (
	"context"
	"database/sql"
	"encoding/binary"
	"encoding/json"
	"fmt"
	"log/slog"
	"math/rand"
	"net/http"
	"os"
	"sort"
	"time"

	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/attribute"
	"go.opentelemetry.io/otel/exporters/otlp/otlpmetric/otlpmetricgrpc"
	"go.opentelemetry.io/otel/exporters/otlp/otlptrace"
	"go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracegrpc"
	"go.opentelemetry.io/otel/metric"
	sdkmetric "go.opentelemetry.io/otel/sdk/metric"
	"go.opentelemetry.io/otel/sdk/resource"
	sdktrace "go.opentelemetry.io/otel/sdk/trace"
	semconv "go.opentelemetry.io/otel/semconv/v1.24.0"
	"go.opentelemetry.io/otel/trace"

	"github.com/gin-gonic/gin"
	"github.com/snowflakedb/gosnowflake"
)

// API endpoints
const (
	StockEndpoint         = "/stock-price"
	TopGainersEndpoint    = "/top-gainers"
	StockExchangeEndpoint = "/stock-exchange"
)

// Global variables
var (
	ServiceName    = "stock_snap_go"
	ServiceHost, _ = os.LookupEnv("SERVICE_HOST")
	ServerPort, _  = os.LookupEnv("SERVER_PORT")

	logger            *slog.Logger
	tracer            trace.Tracer
	meter             metric.Meter
	requestCounter    metric.Int64Counter
	responseHistogram metric.Float64Histogram

	stockPrices map[string]float64

	sfConfig gosnowflake.Config // Snowflake configuration
)

// SnowflakeTraceIdGenerator generates trace IDs incorporating a timestamp component to ensure both uniqueness and traceability.
// Generated trace ID consists of a leading section derived from the timestamp and a trailing section composed of a random suffix.
// Using this generator is required for Snowflake to display traces & spans in Snowsight UI.
type SnowflakeTraceIDGenerator struct{}

func (g SnowflakeTraceIDGenerator) NewIDs(ctx context.Context) (trace.TraceID, trace.SpanID) {
	var traceIDBytes [16]byte
	timestampInMinutes := time.Now().Unix() / 60
	binary.BigEndian.PutUint32(traceIDBytes[:4], uint32(timestampInMinutes))

	for i := 4; i < 16; i++ {
		traceIDBytes[i] = byte(rand.Intn(256))
	}
	var spanIDBytes [8]byte
	for i := range 8 {
		spanIDBytes[i] = byte(rand.Intn(256))
	}
	return trace.TraceID(traceIDBytes), trace.SpanID(spanIDBytes)
}

func (g SnowflakeTraceIDGenerator) NewSpanID(ctx context.Context, traceID trace.TraceID) trace.SpanID {
	var spanIDBytes [8]byte
	for i := range 8 {
		spanIDBytes[i] = byte(rand.Intn(256))
	}
	return trace.SpanID(spanIDBytes)
}

func init() {
	ctx := context.Background()

	setUpLogging()

	setupOTelTracing(ctx)
	tracer = otel.Tracer(ServiceName)

	setUpMetrics(ctx)
	meter = otel.GetMeterProvider().Meter(ServiceName)

	setSnowflakeConfig()

	loadStockPrices("stock-snap.json")
}

func main() {
	router := gin.Default()
	router.Use(addNewlineMiddleware())

	setupRoutes(router)

	requestCounter, _ = meter.Int64Counter(
		"request_count",
		metric.WithDescription("Counts the number of requests"),
	)
	responseHistogram, _ = meter.Float64Histogram(
		"response_latency",
		metric.WithDescription("Response latency"),
		metric.WithUnit("ms"),
	)
	_, _ = meter.Int64ObservableGauge(
		"stock_count",
		metric.WithDescription("Number of stock entries"),
		metric.WithUnit("count"),
		metric.WithInt64Callback(
			func(_ context.Context, obs metric.Int64Observer) error {
				obs.Observe(int64(len(stockPrices)))
				return nil
			},
		),
	)

	serverAddr := fmt.Sprintf("%s:%s", ServiceHost, ServerPort)
	logger.Info("Starting server", "address", serverAddr)

	if err := router.Run(serverAddr); err != nil {
		logger.Error("Failed to start server", "error", err)
		os.Exit(1)
	}
}

func setUpLogging() {
	handler := getHandler()
	logger = slog.New(handler)
	slog.SetDefault(logger)
}

func setUpMetrics(ctx context.Context) {
	exporter, _ := otlpmetricgrpc.New(ctx)
	reader := sdkmetric.NewPeriodicReader(exporter, sdkmetric.WithInterval(5*time.Second))
	provider := sdkmetric.NewMeterProvider(sdkmetric.WithReader(reader))
	otel.SetMeterProvider(provider)
}

func setupOTelTracing(ctx context.Context) {
	res, _ := resource.New(ctx,
		resource.WithAttributes(semconv.ServiceNameKey.String(ServiceName)),
	)
	exporter, _ := otlptrace.New(ctx,
		otlptracegrpc.NewClient(
			otlptracegrpc.WithInsecure(),
		),
	)

	traceIDGenerator := SnowflakeTraceIDGenerator{}

	bsp := sdktrace.NewBatchSpanProcessor(exporter)
	tp := sdktrace.NewTracerProvider(
		sdktrace.WithResource(res),
		sdktrace.WithSpanProcessor(bsp),
		sdktrace.WithIDGenerator(traceIDGenerator),
	)
	otel.SetTracerProvider(tp)
}

func getHandler() *slog.TextHandler {
	handler := slog.NewTextHandler(os.Stdout, &slog.HandlerOptions{
		ReplaceAttr: func(groups []string, a slog.Attr) slog.Attr {
			if a.Key == slog.TimeKey {
				a.Value = slog.StringValue(a.Value.Time().Format("2006-01-02 15:04:05"))
			}
			return a
		},
	})
	return handler
}

func loadStockPrices(filename string) {
	fileContent, err := os.ReadFile(filename)
	if err != nil {
		logger.Error("Failed to load stock prices", "error", err)
		os.Exit(1)
	}

	err = json.Unmarshal(fileContent, &stockPrices)
	if err != nil {
		logger.Error("Failed to unmarshal stock prices", "error", err)
		os.Exit(1)
	}
}

func getLoginToken() string {
	fileContent, _ := os.ReadFile("/snowflake/session/token")
	loginToken := string(fileContent)
	return loginToken
}

func setSnowflakeConfig() {
	// Snowpark Container Services (SPCS) provides many of the variables needed for a connection
	// in the service container's environment
	sfConfig = gosnowflake.Config{
		Account:       os.Getenv("SNOWFLAKE_ACCOUNT"),
		User:          os.Getenv("SNOWFLAKE_USER"),
		Role:          os.Getenv("SNOWFLAKE_ROLE"),
		Authenticator: gosnowflake.AuthTypeOAuth,
		Token:         getLoginToken(),
		Warehouse:     os.Getenv("SNOWFLAKE_WAREHOUSE"),
		Database:      os.Getenv("SNOWFLAKE_DATABASE"),
		Schema:        os.Getenv("SNOWFLAKE_SCHEMA"),
		Host:          os.Getenv("SNOWFLAKE_HOST"),
	}
}

func addNewlineMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		c.Next() // Process the request
		c.Writer.WriteString("\n")
	}
}

func randomSleep() {
	time.Sleep(time.Duration(1+rand.Intn(1000)) * time.Millisecond)
}

// setupRoutes configures all API endpoints
func setupRoutes(router *gin.Engine) {
	router.GET(StockEndpoint, getStockPrice)
	router.GET(TopGainersEndpoint, getTopGainers)
	router.GET(StockExchangeEndpoint, getStockExchange)

	router.GET("/health", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{"status": "up"})
	})
}

// Handler functions

// getStockPrice returns the stock price for the given symbol
func getStockPrice(c *gin.Context) {
	// Root span
	ctx, span := tracer.Start(context.Background(), "get_stock_price")

	startTime := time.Now()
	symbol := c.Query("symbol")

	// Validate input span
	_, childSpan := tracer.Start(ctx, "validate_input")

	_, exists := stockPrices[symbol]
	if symbol == "" || !exists {
		logger.Info(fmt.Sprintf("GET %s - 400 - Invalid symbol", StockEndpoint))
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid symbol"})
		span.AddEvent("response", trace.WithAttributes(
			attribute.Int("http.status_code", http.StatusBadRequest),
			attribute.String("response.body", `{"error": "Invalid symbol"}`),
		))
		return
	}
	randomSleep() // Simulate validation delay

	childSpan.End()

	// Stock price span
	_, childSpan = tracer.Start(ctx, "fetch_price")

	price := stockPrices[symbol]
	randomSleep() // Simulate fetching delay

	childSpan.End()

	// Metrics and logging
	responseTime := time.Since(startTime).Milliseconds()
	responseHistogram.Record(ctx, float64(responseTime), metric.WithAttributes(attribute.String("endpoint", StockEndpoint)))
	requestCounter.Add(ctx, 1, metric.WithAttributes(attribute.String("endpoint", StockEndpoint)))

	span.AddEvent("response", trace.WithAttributes(
		attribute.Int("http.status_code", http.StatusOK),
		attribute.String("response.body", fmt.Sprintf(`{"symbol": "%s", "price": %f}`, symbol, price)),
	))
	span.End()

	logger.Info(fmt.Sprintf("GET %s - 200 - %s: %f", StockEndpoint, symbol, price))

	c.JSON(http.StatusOK, gin.H{"symbol": symbol, "price": price})
}

// getTopGainers returns the top 5 stocks by price
func getTopGainers(c *gin.Context) {
	// Root span
	ctx, span := tracer.Start(context.Background(), "get_top_gainers")
	startTime := time.Now()

	// Fetch prices span
	_, childSpan := tracer.Start(ctx, "fetch_prices")

	sortedStocks := make([]struct {
		Symbol string
		Price  float64
	}, 0, len(stockPrices))

	for symbol, price := range stockPrices {
		sortedStocks = append(sortedStocks, struct {
			Symbol string
			Price  float64
		}{Symbol: symbol, Price: price})
	}

	childSpan.End()

	// Sort and filter span
	_, childSpan = tracer.Start(ctx, "sort_and_filter")

	sort.Slice(sortedStocks, func(i, j int) bool {
		return sortedStocks[i].Price > sortedStocks[j].Price
	})
	sortedStocks = sortedStocks[:5]

	childSpan.End()

	// Metrics and logging
	responseTime := time.Since(startTime).Milliseconds()
	responseHistogram.Record(ctx, float64(responseTime), metric.WithAttributes(attribute.String("endpoint", TopGainersEndpoint)))
	requestCounter.Add(ctx, 1, metric.WithAttributes(attribute.String("endpoint", TopGainersEndpoint)))

	span.AddEvent("response", trace.WithAttributes(
		attribute.Int("http.status_code", http.StatusOK),
		attribute.String("response.body", fmt.Sprintf(`{"top_gainers": %v}`, sortedStocks)),
	))
	span.End()

	logger.Info(fmt.Sprintf("GET %s - 200 - %v", TopGainersEndpoint, sortedStocks))

	c.IndentedJSON(http.StatusOK, gin.H{"top_gainers": sortedStocks})
}

// getStockExchange returns the stock exchange a given symbol is listed on
func getStockExchange(c *gin.Context) {
	// Root span
	ctx, span := tracer.Start(context.Background(), "get_stock_exchange")
	startTime := time.Now()

	// Validate input span
	_, childSpan := tracer.Start(ctx, "validate_input")

	symbol := c.Query("symbol")
	if symbol == "" {
		logger.Info(fmt.Sprintf("GET %s - 400 - Invalid symbol.", StockExchangeEndpoint))
		span.AddEvent("response", trace.WithAttributes(
			attribute.Int("http.status_code", http.StatusBadRequest),
			attribute.String("response.body", `{"error": "Invalid symbol."}`),
		))
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid symbol."})
		return
	}
	randomSleep() // Simulate validation delay

	childSpan.End()

	// Fetch exchange span
	childCtx, childSpan := tracer.Start(ctx, "fetch_exchange")

	// Snowflake connection
	config := &sfConfig
	connector := gosnowflake.NewConnector(gosnowflake.SnowflakeDriver{}, *config)
	db := sql.OpenDB(connector)
	if err := db.Ping(); err != nil {
		logger.Info(fmt.Sprintf("GET %s - 500 - Failed to connect to Snowflake: %v", StockExchangeEndpoint, err))
		span.AddEvent("response", trace.WithAttributes(
			attribute.Int("http.status_code", http.StatusInternalServerError),
			attribute.String("response.body", fmt.Sprintf("Failed to connect to Snowflake: %v", err)),
		))
		c.JSON(http.StatusInternalServerError, gin.H{"error": fmt.Sprintf("Failed to connect to Snowflake: %v", err)})
		return
	}
	defer db.Close()

	// Snowflake query
	query := fmt.Sprintf(
		"SELECT exchange FROM %s.%s.%s WHERE symbol = '%s'", sfConfig.Database,
		sfConfig.Schema, "STOCK_EXCHANGES", symbol,
	)
	rows, err := db.QueryContext(childCtx, query)
	if err != nil {
		logger.Info(fmt.Sprintf("GET %s - 500 - Failed to execute query: %v", StockExchangeEndpoint, err))
		span.AddEvent("response", trace.WithAttributes(
			attribute.Int("http.status_code", http.StatusInternalServerError),
			attribute.String("response.body", fmt.Sprintf("Failed to execute query: %v", err)),
		))
		c.JSON(http.StatusInternalServerError, gin.H{"error": fmt.Sprintf("Failed to execute query: %v", err)})
		return
	}
	defer rows.Close()
	logger.Info("Successful connection and query to Snowflake.")

	// Extract exchange from query response
	var exchange string
	if rows.Next() {
		if err := rows.Scan(&exchange); err != nil {
			logger.Info(fmt.Sprintf("GET %s - 500 - Failed to scan exchange: %v", StockExchangeEndpoint, err))
			span.AddEvent("response", trace.WithAttributes(
				attribute.Int("http.status_code", http.StatusInternalServerError),
				attribute.String("response.body", fmt.Sprintf("Failed to scan exchange: %v", err)),
			))
			c.JSON(http.StatusInternalServerError, gin.H{"error": fmt.Sprintf("Failed to scan exchange: %v", err)})
			return
		}
	} else {
		logger.Info(fmt.Sprintf("GET %s - 404 - Symbol not found.", StockExchangeEndpoint))
		span.AddEvent("response", trace.WithAttributes(
			attribute.Int("http.status_code", http.StatusNotFound),
			attribute.String("response.body", `{"error": "Symbol not found."}`),
		))
		c.JSON(http.StatusNotFound, gin.H{"error": "Symbol not found."})
		return
	}

	childSpan.End()

	// Metrics and logging
	responseTime := time.Since(startTime).Milliseconds()
	responseHistogram.Record(ctx, float64(responseTime), metric.WithAttributes(attribute.String("endpoint", StockExchangeEndpoint)))
	requestCounter.Add(ctx, 1, metric.WithAttributes(attribute.String("endpoint", StockExchangeEndpoint)))

	span.AddEvent("response", trace.WithAttributes(
		attribute.Int("http.status_code", http.StatusOK),
		attribute.String("response.body", fmt.Sprintf(`{"exchange": "%s"}`, exchange)),
	))
	span.End()

	logger.Info(fmt.Sprintf("GET %s - 200 - %s", StockExchangeEndpoint, exchange))

	c.JSON(http.StatusOK, gin.H{"exchange": exchange})
}
