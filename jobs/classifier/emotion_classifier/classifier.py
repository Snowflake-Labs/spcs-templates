import os
from typing import List, Dict, Any

import torch
from transformers import pipeline, AutoModelForSequenceClassification, AutoTokenizer

from emotion_classifier.utils import init_logger

logger = init_logger("TextClassifier")


class EmotionClassifier:
    def __init__(self, config: Dict[str, Any], batch_size: int):
        self._config = config
        self._classifier_pipeline = self._create_classifier_pipeline(
            _get_cuda_device(),
            batch_size,
            config["general"]["model_name"],
        )

    def classify(self, input_texts: List[str]) -> List[str]:
        classifier_outputs = self._classifier_pipeline(input_texts)
        max_scores_outputs = []
        for output_list in classifier_outputs:
            max_scores_outputs.append(str(output_list))
        return max_scores_outputs

    def _create_classifier_pipeline(
        self, device: int, batch_size: int, model_name: str
    ):
        num_gpus = torch.cuda.device_count()
        logger.info(f"Creating classifier pipeline, available gpus: {num_gpus}")

        model = AutoModelForSequenceClassification.from_pretrained(model_name)
        tokenizer = AutoTokenizer.from_pretrained(model_name)

        classifier = pipeline(
            "text-classification",
            model=model,
            tokenizer=tokenizer,
            top_k=2,
            device=torch.device(
                f"cuda:{device}" if torch.cuda.is_available() else "cpu"
            ),
            batch_size=batch_size,
        )
        return classifier


def _get_cuda_device() -> int:
    """
    Each job instance has isolated GPU that always starts with 0
    :return: the cuda device that will be used
    """
    return 0
