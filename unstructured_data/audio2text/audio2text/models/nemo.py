from typing import List
import numpy as np
from audio2text.utils import InputRow, OutputRow
import torch
from nemo.collections.asr.models import EncDecMultiTaskModel
import nemo.collections.asr as nemo_asr


class Model:
    def __init__(self, model_name: str = 'nvidia/canary-1b', device: torch.device = None):
        if device is None:
            device = torch.device("cpu")
        self._model_type = "nemo-canary"
        self._device = device
        self._model_name = model_name
        self._model = self._get_nemo_model()

    def _get_nemo_model(self):
        if self._model_name == 'nvidia/canary-1b':
            model = EncDecMultiTaskModel.from_pretrained(self._model_name, map_location=self._device)
            decode_cfg = self._model.cfg.decoding
            decode_cfg.beam.beam_size = 1
            model.change_decoding_strategy(decode_cfg)
        elif self._model_name == 'nvidia/parakeet-tdt-1.1b':
            model = nemo_asr.models.EncDecRNNTBPEModel.from_pretrained(model_name=self._model_name)
        else:
            raise Exception(f"Unknown model: {self._model_name}, known: [nvidia/canary-1b, nvidia/parakeet-tdt-1.1b]")
        model.eval()
        return model

    def transcribe_batch(self, audio_batch: List[InputRow]) -> List[OutputRow]:
        input_data_batch = [row.filepath for row in audio_batch]
        if self._model_name == 'nvidia/canary-1b':
            transcriptions = self._model.transcribe(
                input_data_batch,
                batch_size=len(input_data_batch),
                pnc='yes',
            )
        else:
            transcriptions = self._model.transcribe(input_data_batch)
        outputs = []
        if isinstance(transcriptions, tuple):
            # for some reason buggy nvidia/parakeet-tdt-1.1b can duplicate the outputs :facepalm
            transcriptions = transcriptions[0]
        for transcription in transcriptions:
            if isinstance(transcription, str):
                outputs.append(OutputRow(text=transcription))
            else:
                outputs.append(OutputRow(text=transcription.text))
        return outputs
