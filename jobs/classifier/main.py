#!/opt/conda/bin/python3

import click
from typing import Dict
from emotion_classifier.classifier import EmotionClassifier
from emotion_classifier.data import get_batch_iterator_from_sql
from emotion_classifier.utils import (
    init_logger,
    load_toml_config,
    get_connection_parameters,
    get_job_name,
    get_rank,
    get_world_size,
)
import snowflake.connector
from snowflake.connector.pandas_tools import write_pandas

logger = init_logger(__name__)


def process(config: Dict[str, str], output_table: str, sql: str, batch_size: int):
    connection_parameters = get_connection_parameters()
    rank, world_size, job_name = get_rank(), get_world_size(), get_job_name()
    with snowflake.connector.connect(**connection_parameters) as conn:
        logger.info(
            f"Starting processing, job: {job_name}, rank: {rank}, world_size: {world_size}, sql: {sql}"
        )
        classifier = EmotionClassifier(config, batch_size)
        cur = conn.cursor()
        batch_idx = 0
        total_records_processed = 0
        for pd_df in get_batch_iterator_from_sql(
            cur, sql, rank, world_size, batch_size
        ):
            total_records_processed += len(pd_df)
            batch_idx += 1
            input_rows = list(pd_df["TEXT"])
            ids = list(pd_df["ID"])
            output_rows = classifier.classify(input_rows)
            output_df = pd_df.assign(OUTPUT=output_rows).reset_index(drop=True)
            write_pandas(conn, output_df, output_table, auto_create_table=True)
            logger.info(
                f"Processed batch: {batch_idx}, total records processed: {total_records_processed}, ids: {ids[0]}-{ids[-1]}"
            )


@click.command()
@click.option("--output-table", required=True, help="Output table to write results")
@click.option("--sql", help="SQL to run")
@click.option("--batch-size", type=int, help="Batch size")
def main(output_table: str, sql: str = None, batch_size: int = 32):
    config = load_toml_config()
    if sql[0] == '"':
        sql = sql[1:-1]
    process(config, output_table, sql, batch_size)


if __name__ == "__main__":
    main()
