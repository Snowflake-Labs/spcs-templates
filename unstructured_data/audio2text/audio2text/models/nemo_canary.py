from typing import List
import numpy as np
from audio2text.utils import InputRow, OutputRow
import torch
from nemo.collections.asr.models import EncDecMultiTaskModel


class Model:
    def __init__(self, model_name: str = 'nvidia/canary-1b', device: torch.device = None):
        if device is None:
            device = torch.device("cpu")
        self._model_type = "nemo-canary"
        self._model = EncDecMultiTaskModel.from_pretrained(model_name, map_location=device)
        decode_cfg = self._model.cfg.decoding
        decode_cfg.beam.beam_size = 1
        self._model.change_decoding_strategy(decode_cfg)
        self._model.eval()

    def transcribe_batch(self, audio_batch: List[InputRow]) -> List[OutputRow]:
        input_data_batch = [row.filepath for row in audio_batch]
        transcriptions = self._model.transcribe(
            input_data_batch,
            batch_size=len(input_data_batch),
            pnc='yes',
        )
        outputs = []
        for transcription in transcriptions:
            if isinstance(transcription, str):
                outputs.append(OutputRow(text=transcription))
            else:
                outputs.append(OutputRow(text=transcription.text))
        return outputs
