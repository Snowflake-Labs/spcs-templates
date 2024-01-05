// spcs.go

package main

import (
	"database/sql"
	"encoding/json"
	"fmt"
	sf "github.com/snowflakedb/gosnowflake"
	"gopkg.in/yaml.v2"
	"io/ioutil"
	"log"
	"net"
	"net/http"
	"os"
	"strings"
)

const (
	ConfigFile          = "config.yaml"
	SpcsPluginName      = "spcs"
	SpcsTokenFilePath   = "/snowflake/session/token"
	ComputePoolQuery    = "SHOW COMPUTE POOLS;"
	RoleQuery           = "SELECT CURRENT_ROLE();"
	NameColumn          = "name"
	StateColumn         = "state"
	OwnerColumn         = "owner"
	StateActiveValue    = "active"
	DnsPrefix           = "metrics"
	DnsSuffix           = "snowflakecomputing.internal"
	MetricsPort         = "9001"
	MetaSpcsPrefix      = SpcsPluginName + "_"
	MetaComputePoolName = "__meta_" + MetaSpcsPrefix + "compute_pool_name"
)

var logger *log.Logger

var config *Config

// Config represents the structure of configuration file
type Config struct {
	Port int `yaml:"port"`
}

// EndpointResolver interface definition
type EndpointResolver interface {
	ResolveEndPoint(endPoint string) ([]string, error)
}

// DNSResolver is a real implementation of EndpointResolver
type DNSResolver struct{}

func getSfConfig() (sf.Config, error) {
	var cfg sf.Config
	var err error
	var token string
	var account = os.Getenv("SNOWFLAKE_ACCOUNT")
	var host = os.Getenv("SNOWFLAKE_HOST")

	token, err = getTokenFromFile(SpcsTokenFilePath)
	cfg = sf.Config{
		Account:       account,
		Host:          host,
		Token:         token,
		Authenticator: sf.AuthTypeOAuth,
	}

	cfg.InsecureMode = true

	if err != nil {
		return cfg, fmt.Errorf("SPCS discovery plugin: Error getting credentials from token file. err: %v", err)
	}
	return cfg, nil
}

func getTokenFromFile(filePath string) (string, error) {
	// Open the file.
	file, err := os.Open(filePath)
	if err != nil {
		return "", err
	}
	// Read the file contents into a string.
	fileContents, err := ioutil.ReadAll(file)
	if err != nil {
		return "", err
	}
	// Close the file.
	defer file.Close()

	return string(fileContents), nil
}

// getDataFromSnowflake establishes a connection with a Snowflake database, executes a query,
// and retrieves the result in the form of rows and column names.
//
// Parameters:
//   - cfg: An sf.Config struct containing Snowflake database configuration.
//   - query: Query to run in Snowflake.
//
// Returns:
//   - rows: A 2D string slice representing the result rows of the executed query.
//   - columns: A string slice containing the names of the columns in the result set.
//   - error: An error, if any, encountered during the database connection, query execution, or data retrieval.
func getDataFromSnowflake(cfg sf.Config, query string) ([][]string, []string, error) {

	// Create DSN from config
	dsn, err := sf.DSN(&cfg)
	if err != nil {
		return nil, nil, fmt.Errorf("SPCS discovery plugin: failed to create DSN from Config. err: %v", err)
	}

	// Establish connection with snowflake
	db, err := sql.Open("snowflake", dsn)
	if err != nil {
		return nil, nil, fmt.Errorf("SPCS discovery plugin: failed to connect. err: %v", err)
	}
	defer db.Close()

	// Execute query
	rows, err := db.Query(query)
	if err != nil {
		return nil, nil, fmt.Errorf("SPCS discovery plugin: failed to run query. %v, err: %v", query, err)
	}
	defer rows.Close()

	// Get column names and types
	columns, err := rows.Columns()
	if err != nil {
		return nil, nil, fmt.Errorf("SPCS discovery plugin: error getting column names. err: %v", err)
	}

	// Create a slice to hold the values
	values := make([]interface{}, len(columns))
	for i := range values {
		var v interface{}
		values[i] = &v
	}

	// Create a slice to store the rows
	var result [][]string

	// Iterate through the rows
	for rows.Next() {
		// Scan the current row into the values slice
		if err := rows.Scan(values...); err != nil {
			return nil, nil, fmt.Errorf("SPCS discovery plugin: error scanning row. err: %v", err)
		}

		// Convert each value to a string and append it to the result slice
		rowValues := make([]string, len(columns))
		for i := range columns {
			if values[i] != nil {
				// Convert the underlying value to a string
				strVal := fmt.Sprintf("%v", *values[i].(*interface{}))
				rowValues[i] = strVal
			}
		}
		result = append(result, rowValues)
	}

	// Check for errors during iteration
	if err := rows.Err(); err != nil {
		return nil, nil, fmt.Errorf("SPCS discovery plugin: Error iterating over rows. err: %v", err)
	}

	return result, columns, nil
}

func getCurrentRole(rows [][]string) (string, error) {

	// Expected to return a single row with one column
	for _, row := range rows {
		role := row[0]
		return role, nil
	}
	return "", fmt.Errorf("SPCS discovery plugin: error retrieving role.")
}

func getComputePoolsToScrape(rows [][]string, columns []string, role string) ([]string, error) {

	// Create a slice to hold the computepools
	var computePools = []string{}

	// Iterate through the rows
	for _, row := range rows {
		cpState, err := getColumnValue(row, columns, StateColumn)
		if err != nil {
			return nil, fmt.Errorf("SPCS discovery plugin: error retrieving compute pool state. %v", err)
		}

		ownerName, err := getColumnValue(row, columns, OwnerColumn)
		if err != nil {
			return nil, fmt.Errorf("SPCS discovery plugin: error retrieving compute pool owner name. %v", err)
		}

		cpName, err := getColumnValue(row, columns, NameColumn)
		if err != nil {
			return nil, fmt.Errorf("SPCS discovery plugin: error retrieving compute pool name. %v", err)
		}

		if strings.ToLower(cpState) == StateActiveValue && strings.ToLower(ownerName) == strings.ToLower(role) {
			computePools = append(computePools, cpName)
		}
	}
	return computePools, nil
}

func getColumnValue(row []string, columns []string, columnName string) (string, error) {

	// Get the column index
	columnIndex := indexOf(columnName, columns)
	if columnIndex == -1 {
		return "", fmt.Errorf("SPCS discovery plugin: column not found. column_name: %v", columnName)
	}

	return row[columnIndex], nil
}

func indexOf(target string, slice []string) int {
	for i, value := range slice {
		if value == target {
			return i
		}
	}
	return -1 // Element not found
}

func getResponse(computePools []string) ([]struct {
	Targets []string          `json:"targets"`
	Labels  map[string]string `json:"labels"`
}, error) {
	// Initialize an empty response slice
	var response []struct {
		Targets []string          `json:"targets"`
		Labels  map[string]string `json:"labels"`
	}

	for _, computePool := range computePools {
		var resolver EndpointResolver = &DNSResolver{}
		targetsForCP, err := getTargets(computePool, resolver)
		labels := getLabels(computePool)

		if err != nil {
			logger.Printf("SPCS discovery plugin: error resolving endpoint: %v", err)
		} else {
			// Append to the response only if there's no error
			response = append(response, struct {
				Targets []string          `json:"targets"`
				Labels  map[string]string `json:"labels"`
			}{
				Targets: targetsForCP,
				Labels:  labels,
			})
		}
	}

	return response, nil
}

func getTargets(computePool string, resolver EndpointResolver) ([]string, error) {
	endPoint := getEndPointFromComputePool(computePool)

	ipAddresses, err := resolver.ResolveEndPoint(endPoint)
	if err != nil {
		return nil, fmt.Errorf("SPCS discovery plugin: error resolving endpoint: %v", err)
	}

	var targetsForCP []string
	for _, ipAddress := range ipAddresses {
		targetForCP := fmt.Sprintf("%s:%s", ipAddress, MetricsPort)
		targetsForCP = append(targetsForCP, targetForCP)
	}

	return targetsForCP, nil
}

func getLabels(computePool string) map[string]string {
	labels := map[string]string{
		MetaComputePoolName: strings.ToLower(computePool),
	}
	return labels
}

func getEndPointFromComputePool(computePool string) string {
	return DnsPrefix + "." + strings.ToLower(computePool) + "." + DnsSuffix
}

func (d *DNSResolver) ResolveEndPoint(endPoint string) ([]string, error) {
	// Resolve the DNS entry to IP addresses.
	ips, err := net.LookupIP(endPoint)
	if err != nil {
		return nil, err
	}

	ipAddresses := []string{}
	for _, ip := range ips {
		ipAddresses = append(ipAddresses, ip.String())
	}

	return ipAddresses, nil
}

func loadConfig(filename string) error {
	// Read the content of the YAML file
	data, err := ioutil.ReadFile(filename)
	if err != nil {
		return fmt.Errorf("error reading config file: %v", err)
	}

	// Parse the YAML content into the Config struct
	err = yaml.Unmarshal(data, &config)
	if err != nil {
		return fmt.Errorf("error unmarshalling config: %v", err)
	}

	return nil
}

func init() {
	// Initialize the logger with timestamp
	logger = log.New(os.Stdout, "", log.Ldate|log.Ltime|log.Lmicroseconds)

	// Load configuration from YAML file
	if err := loadConfig(ConfigFile); err != nil {
		logger.Printf("SPCS discovery plugin: Error loading configuration: %v", err)
	}
}

func main() {
	// Define a handler function
	handler := func(w http.ResponseWriter, r *http.Request) {

		cfg, err := getSfConfig()
		if err != nil {
			logger.Printf("SPCS discovery plugin: Error getting snowflake config to scrape. err: %v", err)
		}

		rows, columns, err := getDataFromSnowflake(cfg, ComputePoolQuery)
		if err != nil {
			logger.Printf("SPCS discovery plugin: Error getting data from snowflake. err: %v", err)
		}

		rolesRows, _, err := getDataFromSnowflake(cfg, RoleQuery)
		if err != nil {
			logger.Printf("SPCS discovery plugin: Error getting data from snowflake. err: %v", err)
		}

		role, err := getCurrentRole(rolesRows)
		if err != nil {
			logger.Printf("SPCS discovery plugin: Error getting current role. err: %v", err)
		}

		computePools, err := getComputePoolsToScrape(rows, columns, role)
		if err != nil {
			logger.Printf("SPCS discovery plugin: Error getting compute pools to scrape. err: %v", err)
		}
		logger.Printf("SPCS discovery plugin: Compute Pools that can be scraped %s\n", computePools)

		response, err := getResponse([]string{})
		if err != nil {
			logger.Printf("SPCS discovery plugin: Error getting targetgroups to scrape. err: %v", err)
		}
		logger.Printf("SPCS discovery plugin response: %s\n", response)

		// Set the HTTP header
		w.Header().Set("Content-Type", "application/json")

		// Encode the response as JSON and write it to the response writer
		err = json.NewEncoder(w).Encode(response)
		if err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}

	}

	// Register the handler for the root ("/") path
	http.HandleFunc("/", handler)

	// Start the HTTP server
	logger.Printf("SPCS discovery plugin: Server listening on port %d...\n", config.Port)
	err := http.ListenAndServe(fmt.Sprintf(":%d", config.Port), nil)
	if err != nil {
		logger.Printf("Error: %s\n", err)
	}
}
