#!/opt/conda/bin/python3

import os
import time

for root, _, files in os.walk("/app/files/audio2text"):
    print(root)

import tempfile
from typing import List
import torch

import click
from evaluate import load
from snowflake.snowpark import Session
from whisper_normalizer.english import EnglishTextNormalizer

from audio2text.data import HFDataset, LibriSpeechDataset
from audio2text.models import openai_whisper, nemo
from audio2text.utils import InputRow
from audio2text.utils import (
    init_logger,
    get_rank,
    get_world_size,
    create_session,
)

logger = init_logger(__name__)


def _process_batch(session: Session, model: openai_whisper.Model, batch_records: List[InputRow], output_table: str,
                   wer, english_normalizer):
    output_rows = model.transcribe_batch(batch_records)
    output_table_batch = []
    for idx in range(len(output_rows)):
        row = {
            'id': batch_records[idx].audio_id,
            'input': batch_records[idx].text,
            'output': output_rows[idx].text,
        }
        output_table_batch.append(row)
    df = session.create_dataframe(output_table_batch)
    df.write.save_as_table(output_table, mode="append")
    norm_predictions = [english_normalizer(row.text) for row in output_rows]
    norm_references = [english_normalizer(row.text) for row in batch_records]
    wer_score = wer.compute(predictions=norm_predictions,
                            references=norm_references)
    return wer_score


def _get_dataset(dataset_type: str, local_dir: str):
    if dataset_type == "hf":
        return HFDataset(local_dir)
    else:
        return LibriSpeechDataset('/data')


def process(
        model: openai_whisper.Model,
        rank: int,
        world_size: int,
        local_dir: str,
        output_table: str,
        dataset_type: str,
        batch_size: int = 2,
):
    wer = load("wer")
    wer_avg_metric = None
    wer_sum_metric = None
    english_normalizer = EnglishTextNormalizer()

    with create_session() as session:
        logger.info(
            f"Starting processing, rank: {rank}, world_size: {world_size}, output_table: {output_table}, local_dir: {local_dir}"
        )
        logger.info("Loading data")
        dataset = _get_dataset(dataset_type, local_dir)

        start_time = time.time()

        for i in range(rank * batch_size, len(dataset), world_size * batch_size):
            batch_start_time = time.time()
            batch_records = dataset[i:i + batch_size]
            wer_score = _process_batch(session, model, batch_records, output_table, wer, english_normalizer)
            if wer_avg_metric is None:
                wer_avg_metric = wer_score
                wer_sum_metric = wer_score
            else:
                wer_avg_metric = (wer_avg_metric + wer_score) / 2
                wer_sum_metric += wer_score
            logger.info(
                f"Processed {i}-{i + batch_size} files, batch_wer_score: {wer_score}, avg_wer_score: {wer_avg_metric}, wer_sum_metric: {wer_sum_metric}, time: {time.time() - batch_start_time}")
        total_time = time.time() - start_time
        logger.info(f"Finished processing, total time: {total_time}")


def get_model(model_type: str, model_name: str, batch_size: int = 8) -> openai_whisper.Model:
    if model_type == "whisper":
        return openai_whisper.Model(model_name, device=get_device(), batch_size=batch_size)
    elif model_type == 'nemo':
        return nemo.Model(model_name, get_device())
    else:
        raise ValueError(f'Unknown model type: {model_type}, supported: [whisper, nemo]]')


def get_device():
    return torch.device("cuda:0" if torch.cuda.is_available() else "cpu")


@click.command()
@click.option("--model-type", help="Model Type")
@click.option("--model-name", help="Model Name")
@click.option("--output-table", help="Output Table")
@click.option("--dataset-type", help="Dataset type")
@click.option("--batch-size", type=int, default=8, help="Batch size")
def main(model_type: str, model_name: str, output_table: str, dataset_type: str, batch_size: int):
    model = get_model(model_type, model_name, batch_size)
    with tempfile.TemporaryDirectory() as temp_dir:
        process(
            model,
            get_rank(),
            get_world_size(),
            temp_dir,
            output_table,
            dataset_type,
            batch_size,
        )


if __name__ == "__main__":
    main()
