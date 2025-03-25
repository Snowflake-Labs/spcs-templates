from typing import List, Generator

from snowflake.connector.result_batch import ArrowResultBatch

from emotion_classifier.utils import init_logger
from pandas.core.frame import DataFrame
from snowflake.connector.cursor import SnowflakeCursor
import pandas as pd

logger = init_logger("DataIterator")


def get_batch_iterator_from_sql(
    cursor: SnowflakeCursor, sql: str, rank: int, world_size: int, batch_size: int
) -> Generator[DataFrame, None, None]:
    """
    Generator to yield batches of files for distributed processing.
    :param cursor: The cursor to execute the SQL query.
    :param sql: The SQL query to execute
    :param rank: The rank of the current worker.
    :param world_size: The total number of workers.
    :param batch_size: The size of each batch.
    :return: Generator yielding batches of files.
    """
    batches = cursor.execute(sql).get_result_batches()
    return get_batch_iterator(batches, rank, world_size, batch_size)


def get_batch_iterator(
    bathces: List[ArrowResultBatch], rank: int, world_size: int, batch_size: int
) -> Generator[DataFrame, None, None]:
    """
    Generator to yield batches of files for distributed processing.
    :param rank: The rank of the current worker.
    :param world_size: The total number of workers.
    :param batch_size: The size of each batch.
    :param files: List of files to be processed.
    :return: Generator yielding batches of files.
    """
    total_records = 0
    for batch in bathces:
        total_records += batch.rowcount
    batch_iter = iter(bathces)
    try:
        next_batch = next(batch_iter)
    except StopIteration:
        return
    curr_data_rows = 0
    cached_dataframe_id = None
    cached_pd_dataframe = None
    # Loop through the batches, skipping the ones that are not for this worker
    for idx in range(rank * batch_size, total_records, world_size * batch_size):
        # Calculate the first and last row of the batch
        first_row, last_row = idx, idx + batch_size - 1
        try:
            while True:
                # Skip the batch if it is not for this worker
                if curr_data_rows + next_batch.rowcount > first_row:
                    break
                curr_data_rows += next_batch.rowcount
                next_batch = next(batch_iter)
            # Load the batch if it is for this worker
            if cached_dataframe_id is None or cached_dataframe_id != next_batch.id:
                pd_batch = next_batch.to_pandas()
                cached_dataframe_id = next_batch.id
                cached_pd_dataframe = pd_batch
            else:
                pd_batch = cached_pd_dataframe

            # Check if the batch is within the current batch
            if last_row < curr_data_rows + next_batch.rowcount:
                # Calculate the start and end row of the batch
                start_row = first_row - curr_data_rows
                end_row = last_row - curr_data_rows
                yield pd_batch.iloc[start_row : end_row + 1]

            else:
                # The batch spans multiple dataframes, so we need to merge them
                start_row = first_row - curr_data_rows
                output = pd_batch.iloc[start_row : next_batch.rowcount]
                try:
                    while last_row >= curr_data_rows + next_batch.rowcount:
                        curr_data_rows += next_batch.rowcount
                        next_batch = next(batch_iter)
                        # Get the data from the batch and add it to the output
                        leftover_data = next_batch.to_pandas().iloc[
                            0 : last_row - curr_data_rows + 1
                        ]
                        output = pd.concat([output, leftover_data])
                except StopIteration:
                    pass  # Iterator is exhausted, stop iteration
                yield output
        except StopIteration:
            pass  # Iterator is exhausted, stop iteration
