// spcs.go

package main

import (
	"encoding/json"
	"fmt"
	"net"
	"net/http"
	"os"
	"strings"

	"github.com/sirupsen/logrus"
	"gopkg.in/yaml.v2"
)

const (
	ConfigFile          = "config.yaml"
	ComputePoolQuery    = "SHOW COMPUTE POOLS;"
	NameColumn          = "name"
	StateColumn         = "state"
	OwnerColumn         = "owner"
	StateActiveValue    = "active"
	DnsPrefix           = "metrics"
	DnsSuffix           = "snowflakecomputing.internal"
	MetricsPort         = "9001"
	MetaComputePoolName = "__meta_spcs_compute_pool_name"
	NOT_FOUND           = -1
)

var config *Config

// Config represents the structure of configuration file
type Config struct {
	Port int `yaml:"port"`
}

// EndpointResolver interface definition
type EndpointResolver interface {
	ResolveEndpoint(endPoint string) ([]string, error)
}

// DNSResolver is a real implementation of EndpointResolver
type DNSResolver struct{}

func (d *DNSResolver) ResolveEndpoint(endPoint string) ([]string, error) {
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

func getCurrentRole(rows [][]string) (string, error) {

	// Expected to return a single row with one column
	for _, row := range rows {
		role := row[0]
		return role, nil
	}
	return "", fmt.Errorf("SPCS discovery plugin: error retrieving role.")
}

func getComputePoolsToScrape(rows [][]string, columns []string) ([]string, error) {

	var computePools = []string{}

	for _, row := range rows {
		cpState, err := getColumnValue(row, columns, StateColumn)
		if err != nil {
			return nil, fmt.Errorf("SPCS discovery plugin: error retrieving compute pool state. %v", err)
		}

		cpName, err := getColumnValue(row, columns, NameColumn)
		if err != nil {
			return nil, fmt.Errorf("SPCS discovery plugin: error retrieving compute pool name. %v", err)
		}

		if strings.ToLower(cpState) == StateActiveValue {
			computePools = append(computePools, cpName)
		}
	}
	return computePools, nil
}

func getColumnValue(row []string, columns []string, columnName string) (string, error) {

	columnIndex := indexOf(columnName, columns)
	if columnIndex == NOT_FOUND {
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
	return NOT_FOUND
}

func getTargetgroups(computePools []string) ([]struct {
	Targets []string          `json:"targets"`
	Labels  map[string]string `json:"labels"`
}, error) {
	var response []struct {
		Targets []string          `json:"targets"`
		Labels  map[string]string `json:"labels"`
	}

	for _, computePool := range computePools {
		var resolver EndpointResolver = &DNSResolver{}
		targetsForCP, err := getTargets(computePool, resolver)
		labels := getLabels(computePool)

		if err != nil {
			logrus.Errorf("SPCS discovery plugin: error resolving endpoint: %v", err)
		} else {
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

	ipAddresses, err := resolver.ResolveEndpoint(endPoint)
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

func loadConfig(filename string) error {
	data, err := os.ReadFile(filename)
	if err != nil {
		return fmt.Errorf("error reading config file: %v", err)
	}

	err = yaml.Unmarshal(data, &config)
	if err != nil {
		return fmt.Errorf("error unmarshalling config: %v", err)
	}

	return nil
}

func init() {
	if err := loadConfig(ConfigFile); err != nil {
		logrus.Errorf("SPCS discovery plugin: Error loading configuration: %v", err)
	}
}

func processRequest() []struct {
	Targets []string          `json:"targets"`
	Labels  map[string]string `json:"labels"`
} {
	cfg, err := GetSfConfig()
	if err != nil {
		logrus.Errorf("SPCS discovery plugin: Error getting snowflake config to scrape. err: %v", err)
	}

	rows, columns, err := GetDataFromSnowflake(cfg, ComputePoolQuery)
	if err != nil {
		logrus.Errorf("SPCS discovery plugin: Error getting data from snowflake. err: %v", err)
	}

	computePools, err := getComputePoolsToScrape(rows, columns)
	if err != nil {
		logrus.Errorf("SPCS discovery plugin: Error getting compute pools to scrape. err: %v", err)
	}
	logrus.Infof("SPCS discovery plugin: Compute Pools that can be scraped %s\n", computePools)

	response, err := getTargetgroups(computePools)
	if err != nil {
		logrus.Errorf("SPCS discovery plugin: Error getting targetgroups to scrape. err: %v", err)
	}
	logrus.Infof("SPCS discovery plugin response: %s\n", response)

	return response
}

func main() {
	handler := func(w http.ResponseWriter, r *http.Request) {

		response := processRequest()

		w.Header().Set("Content-Type", "application/json")

		// Encode the response as JSON and write it to the response writer
		err := json.NewEncoder(w).Encode(response)
		if err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}

	}

	http.HandleFunc("/", handler)

	logrus.Infof("SPCS discovery plugin: Server listening on port %d...\n", config.Port)
	err := http.ListenAndServe(fmt.Sprintf(":%d", config.Port), nil)
	if err != nil {
		logrus.Errorf("Error: %s\n", err)
	}
}
