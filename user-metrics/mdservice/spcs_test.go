// spcs_test.go

package main

import (
	"strings"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestGetComputePoolsToScrape(t *testing.T) {
	// Test case with a single row, where cpState is active
	rows := [][]string{
		{"active", "pool1", "admin"},
	}
	columns := []string{"state", "name", "owner"}
	role := "admin"
	expected := []string{"pool1"}
	result, err := getComputePoolsToScrape(rows, columns, role)
	verifyResult(t, err, result, expected)

	// Test case with multiple rows, some active and some inactive
	rows = [][]string{
		{"active", "pool1", "admin"},
		{"inactive", "pool2", "admin"},
		{"active", "pool3", "admin"},
	}
	expected = []string{"pool1", "pool3"}
	result, err = getComputePoolsToScrape(rows, columns, role)
	verifyResult(t, err, result, expected)

	// Test case with no active compute pools
	rows = [][]string{
		{"inactive", "pool1", "admin"},
		{"inactive", "pool2", "admin"},
	}
	expected = []string{}
	result, err = getComputePoolsToScrape(rows, columns, role)
	verifyResult(t, err, result, expected)

	// Test case with active compute pools but different owner
	// Should list only the compute pools that are created from same role as service
	rows = [][]string{
		{"active", "pool1", "admin"},
		{"active", "pool2", "guest"},
	}
	expected = []string{"pool1"}
	result, err = getComputePoolsToScrape(rows, columns, role)
	verifyResult(t, err, result, expected)

	// Test case with no state column
	rows = [][]string{
		{"pool1", "admin"},
		{"pool2", "admin"},
	}
	columns = []string{"name", "owner"}
	expected = []string{}
	result, err = getComputePoolsToScrape(rows, columns, role)
	if err == nil {
		t.Errorf("Expected an error, but got no error")
	}
	require.Equal(t, "SPCS discovery plugin: error retrieving compute pool state. SPCS discovery plugin: column not found. column_name: state", err.Error(), "Error message mismatch")
}

func TestGetColumnValue(t *testing.T) {
	// Test case where the column exists
	row := []string{"value1", "value2", "value3"}
	columns := []string{"column1", "column2", "column3"}
	columnName := "column2"

	result, err := getColumnValue(row, columns, columnName)

	// Assert that there is no error and the result is as expected
	assert.NoError(t, err)
	assert.Equal(t, "value2", result)

	// Test case where the column does not exist
	columnName = "nonexistent_column"
	result, err = getColumnValue(row, columns, columnName)

	// Assert that an error is returned and the result is an empty string
	assert.Error(t, err)
	assert.Equal(t, "", result)
}

func TestGetTargets(t *testing.T) {
	// Create a mock resolver for testing.
	mockResolver := &MockEndpointResolver{}

	// Resolving a compute pool with one node
	computePool := "Pool1"
	mockResolver.ipAddresses = []string{"1.2.3.4"}
	resultTargets, err := getTargets(computePool, mockResolver)
	expectedTargets := []string{"1.2.3.4:" + MetricsPort}
	verifyResult(t, err, resultTargets, expectedTargets)

	// Resolving a compute pool with two nodes
	computePool = "Pool1"
	mockResolver.ipAddresses = []string{"1.2.3.4", "5.6.7.8"}
	resultTargets, err = getTargets(computePool, mockResolver)
	expectedTargets = []string{"1.2.3.4:" + MetricsPort, "5.6.7.8:" + MetricsPort}
	verifyResult(t, err, resultTargets, expectedTargets)

	computePool = ""
	resultTargets, err = getTargets(computePool, &DNSResolver{})
	if err == nil {
		t.Errorf("Expected an error, but got no error")
	}
	require.Equal(t, "SPCS discovery plugin: error resolving endpoint: lookup metrics..snowflakecomputing.internal: no such host", err.Error(), "Error message mismatch")

	// DNS Resolution Failed
	computePool = "Pool1"
	resultTargets, err = getTargets(computePool, &DNSResolver{})
	if err == nil {
		t.Errorf("Expected an error, but got no error")
	}
	require.Equal(t, "SPCS discovery plugin: error resolving endpoint: lookup metrics.pool1.snowflakecomputing.internal: no such host", err.Error(), "Error message mismatch")

}

// Mock resolver for testing.
type MockEndpointResolver struct {
	ipAddresses []string
}

func (m *MockEndpointResolver) ResolveEndpoint(endPoint string) ([]string, error) {
	// Return predefined IP addresses for testing.
	return m.ipAddresses, nil
}

func removeLeadingSpaces(input string) string {
	lines := strings.Split(input, "\n")
	for i, line := range lines {
		lines[i] = strings.TrimLeft(line, " \t")
	}
	return strings.Join(lines, "\n")
}

func getEndPoint(input string) string {
	return DnsPrefix + "." + strings.ToLower(input) + "." + DnsSuffix
}

func verifyResult(t *testing.T, err error, result []string, expected []string) {
	if err != nil {
		t.Errorf("Expected no error, but got an error: %v", err)
	}
	if len(result) != len(expected) {
		t.Errorf("Expected %v, but got %v", expected, result)
	}
	for i := range expected {
		if result[i] != expected[i] {
			t.Errorf("Expected %v, but got %v", expected[i], result[i])
		}
	}
}
