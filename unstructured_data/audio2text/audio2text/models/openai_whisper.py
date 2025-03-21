import numpy as np
import torch
from typing import Dict
from transformers import WhisperProcessor, WhisperForConditionalGeneration


class Model:
    def __init__(self, config: Dict):
        self._model_type = "whisper-hf"
        self._model_name = config["general"]["model_name"]
        self._processor = WhisperProcessor.from_pretrained(self._model_name)
        self._model = WhisperForConditionalGeneration.from_pretrained(
            self._model_name,
            attn_implementation=config["general"]["attention_implementation"],
        )

        # Enable static cache and compile the forward pass
        self._model.generation_config.cache_implementation = config["general"][
            "cache_implementation"
        ]
        self._model.forward = torch.compile(
            self._model.forward, mode="reduce-overhead", fullgraph=True
        )

    def transcribe_batch(self, audio_batch: np.ndarray):
        input_features = self._processor(
            audio_batch, return_tensors="pt", sampling_rate=16000
        ).input_features

        # Generate token ids using compiled graph (fast!)
        predicted_ids = self._model.generate(input_features)

        # Decode token ids to text
        transcription = self._processor.batch_decode(
            predicted_ids, skip_special_tokens=True
        )
        return transcription
