import os
from typing import List

import torch
from transformers import pipeline, AutoModelForSequenceClassification, AutoTokenizer

from spcs_utils import init_logger, InputRow, OutputRow, ModelConfiguration

logger = init_logger("TextClassifier")

classifier_pipeline = None


def run_classifier(rows: List[InputRow], batch_size: int, model_config: ModelConfiguration) -> List[OutputRow]:
    """
    Main function that uses model and tokenizer to produce text classification
    :param rows: List of input rows
    :param batch_size: Batch size that will be used by the hf pipeline
    :param model_config: model and tokenizer config
    :return: --
    """
    texts = [row.text for row in rows]
    global classifier_pipeline
    if classifier_pipeline is None:
        classifier_pipeline = _create_classifier_pipeline(_get_cuda_device(), batch_size, model_config)
    classifier_outputs = classifier_pipeline(texts)
    max_scores_outputs = []
    for output_list in classifier_outputs:
        max_scores_outputs.append(str(output_list))
    return [OutputRow(idx=rows[idx].idx, output=max_scores_outputs[idx]) for idx in range(len(max_scores_outputs))]


def _create_classifier_pipeline(device: int, batch_size: int, model_config: ModelConfiguration):
    num_gpus = torch.cuda.device_count()
    logger.info(f"Creating classifier pipeline on worker: {os.getpid()}, available gpus: {num_gpus}")

    model = AutoModelForSequenceClassification.from_pretrained(model_config.classifier_model_name)
    tokenizer = AutoTokenizer.from_pretrained(model_config.classifier_model_name)

    classifier = pipeline(
        "text-classification",
        model=model,
        tokenizer=tokenizer,
        top_k=2,
        device=torch.device(f"cuda:{device}" if torch.cuda.is_available() else "cpu"),
        batch_size=batch_size)
    return classifier


def _get_cuda_device() -> int:
    """
    Each job instance has isolated GPU that always starts with 0
    :return: the cuda device that will be used
    """
    return 0
