package main

import (
	"flag"
	"fmt"
	"log"
	"net/http"
	"net/http/httputil"
	"net/url"
	"strconv"
	"time"

	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promhttp"
)

var (
	target   = flag.String("target", "", "Target url to send requests to. Example: http://127.0.0.1:8000")
	port     = flag.Int("port", 0, "Goproxy port")
	requests = flag.Int("requests", 0, "Number of requests that can be processed in parallel by downstream service")
	debug    = flag.Bool("debug", false, "Print debug logs")

	processedRequests = prometheus.NewCounterVec(
		prometheus.CounterOpts{
			Name: "http_proxy_requests_total",
			Help: "Total number of requests redirected by the proxy",
		},
		[]string{"method", "code"},
	)
	requestDuration = prometheus.NewHistogramVec(
		prometheus.HistogramOpts{
			Name:    "http_proxy_request_duration_seconds",
			Help:    "Histogram of request durations in seconds",
			Buckets: prometheus.DefBuckets,
		},
		[]string{"method", "path"},
	)
)

type GoProxy struct {
	proxy     *httputil.ReverseProxy
	semaphore chan struct{}
}

func NewGoProxy(target string, maxConcurrentRequests int) *GoProxy {
	url, err := url.Parse(target)
	if err != nil {
		log.Fatalf("Failed to parse target URL: %v", err)
	}

	proxy := httputil.NewSingleHostReverseProxy(url)

	return &GoProxy{
		proxy:     proxy,
		semaphore: make(chan struct{}, maxConcurrentRequests),
	}
}

func (p *GoProxy) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	select {
	case p.semaphore <- struct{}{}:
		start := time.Now()

		defer func() { <-p.semaphore }()
		if *debug {
			log.Printf("Redirecting request")
		}
		p.proxy.ServeHTTP(w, r)

		duration := time.Since(start).Seconds()
		requestDuration.WithLabelValues(r.Method, r.URL.Path).Observe(duration)
		processedRequests.WithLabelValues(r.Method, strconv.Itoa(http.StatusOK)).Inc()
	default:
		if *debug {
			log.Printf("429: All requests are busy, try later")
		}
		processedRequests.WithLabelValues(r.Method, strconv.Itoa(http.StatusTooManyRequests)).Inc()
		http.Error(w, "429: All requests are busy, try later", http.StatusTooManyRequests)
	}
}

func validateTargetUrl(targetUrl string) error {
	parsedURL, err := url.Parse(targetUrl)
	if err != nil {
		return fmt.Errorf("invalid URL")
	}
	if parsedURL.Hostname() == "" {
		return fmt.Errorf("invalid URL: domain is missing")
	}
	if parsedURL.Port() == "" {
		return fmt.Errorf("invalid URL: port is missing")
	}
	return nil
}

func main() {
	prometheus.MustRegister(processedRequests)
	prometheus.MustRegister(requestDuration)

	flag.Parse()
	if *target == "" {
		log.Fatalf("Error: -target is required parameter")
	}
	err := validateTargetUrl(*target)
	if err != nil {
		log.Fatalf("Error: -target has incorrect value, expected format: http://0.0.0.0:9000")
	}

	if *port <= 0 || *port > 65535 {
		log.Fatalf("Error: -port is required parameter between 1 and 65535")
	}

	if *requests <= 0 {
		log.Fatalf("Error: -requests is required parameter")
	}

	goProxy := NewGoProxy(*target, *requests)

	mux := http.NewServeMux()
	mux.Handle("/", goProxy)
	mux.Handle("/metrics", promhttp.Handler())

	listenAddr := fmt.Sprintf(":%d", *port)
	log.Printf("Starting proxy server on port %d, forwarding to %s\n", *port, *target)
	if err := http.ListenAndServe(listenAddr, mux); err != nil {
		log.Fatalf("Could not start server: %v", err)
	}
}
