from typing import List

import torch
from audio2text.utils import InputRow, OutputRow
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline


class Model:
    def __init__(self, model_name: str = "openai/whisper-tiny.en", device: torch.device = None, batch_size: int = 8):
        if device is None:
            self._device = torch.device("cpu")
        else:
            self._device = device
        self._model_type = "whisper-hf"
        self._model_name = model_name

        torch_dtype = torch.float32

        model = AutoModelForSpeechSeq2Seq.from_pretrained(
            model_name, torch_dtype=torch_dtype, low_cpu_mem_usage=True, use_safetensors=True
        )
        model.to(device)
        processor = AutoProcessor.from_pretrained(model_name)
        self.pipe = pipeline(
            "automatic-speech-recognition",
            model=model,
            tokenizer=processor.tokenizer,
            feature_extractor=processor.feature_extractor,
            max_new_tokens=256,
            chunk_length_s=30,
            batch_size=batch_size,
            return_timestamps=True,
            torch_dtype=torch_dtype,
            device=device,
        )

    def transcribe_batch(self, audio_batch: List[InputRow]) -> List[OutputRow]:
        input_data_batch = [row.filepath for row in audio_batch]

        predictions = self.pipe(input_data_batch)
        return [
            OutputRow(
                text=row['text']
            ) for row in predictions
        ]
