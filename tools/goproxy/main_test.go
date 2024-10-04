package main

import (
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"github.com/stretchr/testify/require"
)

func TestValidateTargetUrl(t *testing.T) {
	tests := []struct {
		name      string
		url       string
		expectErr bool
	}{
		{"Valid URL", "http://localhost:8080", false},
		{"Missing port", "http://localhost", true},
		{"Missing domain", "http://:8080", true},
		{"Invalid URL", "not_a_url", true},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			err := validateTargetUrl(tt.url)
			if (err != nil) != tt.expectErr {
				t.Errorf("validateTargetUrl(%s) = %v, expected error: %v", tt.url, err, tt.expectErr)
			}
		})
	}
}

func TestNewGoProxy(t *testing.T) {
	goproxy := NewGoProxy("http://localhost:8080", 4)
	require.NotNil(t, goproxy)
	require.NotNil(t, goproxy.proxy)
	require.Equal(t, 4, cap(goproxy.semaphore))
}

func TestServeHTTPNormal(t *testing.T) {
	targetServer := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		w.Write([]byte("dummy message"))
	}))
	defer targetServer.Close()

	proxy := NewGoProxy(targetServer.URL, 1)
	server := httptest.NewServer(http.HandlerFunc(proxy.ServeHTTP))
	defer server.Close()

	req, err := http.NewRequest("GET", server.URL, nil)
	require.NoError(t, err)

	resp, err := http.DefaultClient.Do(req)
	require.NoError(t, err)
	require.Equal(t, resp.StatusCode, http.StatusOK)
}

func TestServeHTTPRateLimiting(t *testing.T) {
	targetServer := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		time.Sleep(500 * time.Millisecond)
		w.WriteHeader(http.StatusOK)
	}))
	defer targetServer.Close()

	proxy := NewGoProxy(targetServer.URL, 1)
	server := httptest.NewServer(http.HandlerFunc(proxy.ServeHTTP))
	defer server.Close()

	go func() {
		time.Sleep(100 * time.Millisecond)
		req1, err := http.NewRequest("GET", server.URL, nil)
		require.NoError(t, err)
		resp1, err := http.DefaultClient.Do(req1)
		require.NoError(t, err)
		require.Equal(t, http.StatusTooManyRequests, resp1.StatusCode)

	}()

	req2, err := http.NewRequest("GET", server.URL, nil)
	require.NoError(t, err)

	resp2, err := http.DefaultClient.Do(req2)
	require.NoError(t, err)
	require.Equal(t, http.StatusOK, resp2.StatusCode)
}
