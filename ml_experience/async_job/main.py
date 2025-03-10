#!/opt/conda/bin/python3

import argparse
import logging
import os
import sys

from snowflake.snowpark import Session
from snowflake.snowpark.functions import col, row_number, when_matched, when_not_matched
from snowflake.snowpark.window import Window
from snowflake.snowpark.exceptions import *

from transformers import pipeline


# Environment variables below will be automatically populated by Snowflake.
SNOWFLAKE_ACCOUNT = os.getenv("SNOWFLAKE_ACCOUNT")
SNOWFLAKE_HOST = os.getenv("SNOWFLAKE_HOST")
SNOWFLAKE_DATABASE = os.getenv("SNOWFLAKE_DATABASE")
SNOWFLAKE_SCHEMA = os.getenv("SNOWFLAKE_SCHEMA")

# Custom environment variables
SNOWFLAKE_USER = os.getenv("SNOWFLAKE_USER")
SNOWFLAKE_PASSWORD = os.getenv("SNOWFLAKE_PASSWORD")
SNOWFLAKE_ROLE = os.getenv("SNOWFLAKE_ROLE")
SNOWFLAKE_WAREHOUSE = os.getenv("SNOWFLAKE_WAREHOUSE")


def get_arg_parser():
    """
    Input argument list.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", required=False, default="summarization", help="task to perform, currently (sentiment or summarization)")
    parser.add_argument("--source_table", required=True, help="database.schema.table containing sentiment data")
    parser.add_argument("--source_id_column", required=True, help="column in source table containing id")
    parser.add_argument("--source_value_column", required=True, help="column in source table containing text value to analyze")
    parser.add_argument("--result_table", required=True, help="name of the table to store sentiment analysis")

    return parser


def get_logger():
    """
    Get a logger for local logging.
    """
    logger = logging.getLogger("job-tutorial")
    logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(name)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger


def get_login_token():
    """
    Read the login token supplied automatically by Snowflake. These tokens
    are short lived and should always be read right before creating any new connection.
    """
    with open("/snowflake/session/token", "r") as f:
        return f.read()


def get_connection_params():
    """
    Construct Snowflake connection params from environment variables.
    """
    if os.path.exists("/snowflake/session/token"):
        return {
            "account": SNOWFLAKE_ACCOUNT,
            "host": SNOWFLAKE_HOST,
            "authenticator": "oauth",
            "token": get_login_token(),
            "warehouse": SNOWFLAKE_WAREHOUSE,
            "database": SNOWFLAKE_DATABASE,
            "schema": SNOWFLAKE_SCHEMA
        }
    else:
        return {
            "account": SNOWFLAKE_ACCOUNT,
            "host": SNOWFLAKE_HOST,
            "user": SNOWFLAKE_USER,
            "password": SNOWFLAKE_PASSWORD,
            "role": SNOWFLAKE_ROLE,
            "warehouse": SNOWFLAKE_WAREHOUSE,
            "database": SNOWFLAKE_DATABASE,
            "schema": SNOWFLAKE_SCHEMA
        }


def run_job():
    """
    Main body of this job.
    """
    logger = get_logger()
    logger.info("Job started")

    # Parse input arguments
    args = get_arg_parser().parse_args()
    task = args.task
    source_table = args.source_table
    source_id_column = args.source_id_column
    source_value_column = args.source_value_column
    result_table = args.result_table

    with Session.builder.configs(get_connection_params()).create() as session:
        # Print out current session context information.
        database = session.get_current_database()
        schema = session.get_current_schema()
        warehouse = session.get_current_warehouse()
        role = session.get_current_role()
        logger.info(
            f"Connection succeeded. Current session context: database={database}, schema={schema}, warehouse={warehouse}, role={role}"
        )

        # Read the source table into a DataFrame
        df = session.table(source_table)

        # Add a row number column to facilitate pagination.
        window_spec = Window.order_by(source_id_column)
        df_with_rn = df.with_column("rn", row_number().over(window_spec))

        # Determine the total number of rows (this will trigger a query)
        total_rows = df_with_rn.count()
        batch_size = 10
        logger.info(
            f"Working with source table [{source_table}], containing {total_rows } rows"
        )

        logger.info(f"Initializing {task} analysis model")
        if task == "sentiment":
            model_path = 'distilbert-base-uncased-finetuned-sst-2-english'
            tokenizer_path = 'distilbert-base-uncased-finetuned-sst-2-english'
            analyzer = pipeline("sentiment-analysis", model=model_path, tokenizer=tokenizer_path)
        else:
            model_path = 'google-t5-small'
            tokenizer_path = 'google-t5-small'
            analyzer = pipeline("summarization", model=model_path, tokenizer=tokenizer_path)

        # Loop through the data in batches
        for start in range(1, total_rows + 1, batch_size):
            end = start + batch_size - 1
            logger.info(
                f"Loaded batch rows {start} - {end}"
            )

            # Filter the DataFrame to the current batch
            batch_df = df_with_rn.filter((col("rn") >= start) & (col("rn") <= end))
            label_col = batch_df.select(col(source_id_column),col(source_value_column))
            rows = label_col.collect()

            analyzed = analyzer([row[source_value_column] for row in rows])
            logger.info(
                f"Completed text analysis over {len(analyzed)} rows"
            )

            # Add back ID
            for i, item in enumerate(analyzed):
                item[source_id_column] = rows[i][source_id_column]

            processed_df = session.createDataFrame(analyzed)

            if task == "sentiment":
                # Sentiment analysis variables
                analyzer_sentiment_label_column = "label"
                analyzer_sentiment_score_column = "score"
                table_sentiment_label_column = "SENTIMENT_LABEL"
                table_sentiment_score_column = "SENTIMENT_SCORE"
            else:
                # Summarization variables
                analyzer_summary_column ="summary_text"
                table_summary_column = "SUMMARY_TEXT"

            try:
                # If table exists       
                result = session.table(result_table)

                if task == "sentiment":
                    # Make sure the columns we need are there
                    if table_sentiment_label_column not in result.columns or table_sentiment_score_column not in result.columns:
                        session.sql(f"ALTER TABLE {result_table} ADD COLUMN {table_sentiment_label_column} VARCHAR, { table_sentiment_score_column} VARCHAR").collect()
                    result = session.table(result_table)

                    # If table exists, do a merge operation using source_id_column as key
                    result.merge(
                        processed_df,
                        (result[source_id_column] == processed_df[source_id_column]),
                        [when_matched().update({
                            table_sentiment_label_column: processed_df[analyzer_sentiment_label_column],
                            table_sentiment_score_column: processed_df[analyzer_sentiment_score_column]
                            }), 
                        when_not_matched().insert({
                            source_id_column: processed_df[source_id_column],
                            table_sentiment_label_column: processed_df[analyzer_sentiment_label_column],
                            table_sentiment_score_column: processed_df[analyzer_sentiment_score_column]})])
                else:
                    # Make sure the columns we need are there
                    if table_summary_column not in result.columns:
                        session.sql(f"ALTER TABLE {result_table} ADD COLUMN {table_summary_column} VARCHAR").collect()
                    result = session.table(result_table)
    
                    # Merge in summarization
                    result.merge(
                        processed_df,
                        (result[source_id_column] == processed_df[source_id_column]),
                        [when_matched().update({
                            table_summary_column: processed_df[analyzer_summary_column]
                            }), 
                        when_not_matched().insert({
                            source_id_column: processed_df[source_id_column],
                            table_summary_column: processed_df[analyzer_summary_column]})])

                logger.info(f"Merged {task} data with existing table [{result_table}]")
            except SnowparkSQLException:
                if task == "sentiment":
                    processed_df = processed_df \
                        .withColumnRenamed(analyzer_sentiment_label_column, table_sentiment_label_column) \
                        .withColumnRenamed(analyzer_sentiment_score_column, table_sentiment_score_column)
                else:
                    processed_df = processed_df \
                        .withColumnRenamed(analyzer_summary_column, table_summary_column)
                
                # If table doesn't exist, create it with all columns (including source_id_column)
                processed_df.write.mode("append").save_as_table(result_table)
                logger.info(f"Created new table [{result_table}] and wrote {task} data")

    logger.info("Job finished")


if __name__ == "__main__":
    run_job()

