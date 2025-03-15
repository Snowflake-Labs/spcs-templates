// sf_utils.go

package main

import (
	"database/sql"
	"fmt"
	"io/ioutil"
	"os"
	"strconv"

	sf "github.com/snowflakedb/gosnowflake"
)

const (
	SpcsTokenFilePath = "/snowflake/session/token"
)

// GetSfConfig retrieves the Snowflake configuration from environment variables
// and the container's token file.
//
// Parameters:
//   - None
//
// Returns:
//   - sf.Config: A configuration struct for the Snowflake client.
//   - error: An error, if any, encountered during the process.
func GetSfConfig() (sf.Config, error) {
	var cfg sf.Config
	var err error
	var token string
	var account = os.Getenv("SNOWFLAKE_ACCOUNT")
	var host = os.Getenv("SNOWFLAKE_HOST")
	var protocol = os.Getenv("SNOWFLAKE_PROTOCOL")
	var portStr = os.Getenv("SNOWFLAKE_PORT")

	port, err := strconv.Atoi(portStr)
	if err != nil {
		return sf.Config{}, fmt.Errorf("Error parsing SNOWFLAKE_PORT", err)
	}

	token, err = getTokenFromFile(SpcsTokenFilePath)
	if err != nil {
		return sf.Config{}, fmt.Errorf(
			"SPCS discovery plugin: Error getting credentials from token file. account: %v host: %v err: %v", account, host, err,
		)
	}

	cfg = sf.Config{
		Account:       account,
		Host:          host,
		Token:         token,
		Authenticator: sf.AuthTypeOAuth,
		Protocol:      protocol,
		Port:          port,
	}

	cfg.InsecureMode = true

	return cfg, nil
}

func getTokenFromFile(filePath string) (string, error) {

	file, err := os.Open(filePath)
	if err != nil {
		return "", err
	}

	fileContents, err := ioutil.ReadAll(file)
	if err != nil {
		return "", err
	}

	defer file.Close()

	return string(fileContents), nil
}

// GetDataFromSnowflake establishes a connection with a Snowflake database, executes a query,
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
func GetDataFromSnowflake(cfg sf.Config, query string) ([][]string, []string, error) {

	dsn, err := sf.DSN(&cfg)
	if err != nil {
		return nil, nil, fmt.Errorf("SPCS discovery plugin: failed to create DSN from Config. err: %v", err)
	}

	db, err := sql.Open("snowflake", dsn)
	if err != nil {
		return nil, nil, fmt.Errorf("SPCS discovery plugin: failed to connect. err: %v", err)
	}
	defer db.Close()

	rows, err := db.Query(query)
	if err != nil {
		return nil, nil, fmt.Errorf("SPCS discovery plugin: failed to run query. %v, err: %v", query, err)
	}
	defer rows.Close()

	columns, err := rows.Columns()
	if err != nil {
		return nil, nil, fmt.Errorf("SPCS discovery plugin: error getting column names. err: %v", err)
	}

	values := make([]interface{}, len(columns))
	for i := range values {
		var v interface{}
		values[i] = &v
	}

	var result [][]string

	for rows.Next() {
		if err := rows.Scan(values...); err != nil {
			return nil, nil, fmt.Errorf("SPCS discovery plugin: error scanning row. err: %v", err)
		}

		// Convert each value to a string and append it to the result slice
		rowValues := make([]string, len(columns))
		for i := range columns {
			if values[i] != nil {
				strVal := fmt.Sprintf("%v", *values[i].(*interface{}))
				rowValues[i] = strVal
			}
		}
		result = append(result, rowValues)
	}

	if err := rows.Err(); err != nil {
		return nil, nil, fmt.Errorf("SPCS discovery plugin: Error iterating over rows. err: %v", err)
	}

	return result, columns, nil
}
