#!/opt/conda/bin/python3

import os
from typing import List, Dict
from datasets import load_dataset
from audio2text.utils import InputRow, load_audio


def get_dataset(data_dir: str, path="facebook/voxpopuli", name="en_accented", split="test"):
    return load_dataset(
        path,
        name,
        split=split,
        data_dir=data_dir,
        cache_dir=data_dir,
        trust_remote_code=True,
    )


class HFDataset:
    def __init__(self, data_dir: str, path="facebook/voxpopuli", name="en_accented", split="test"):
        self._dataset = load_dataset(
            path,
            name,
            split=split,
            data_dir=data_dir,
            cache_dir=data_dir,
            trust_remote_code=True,
        )

    def _to_input_row(self, items, idx: int) -> InputRow:
        return InputRow(
            audio_id=items['audio_id'][idx],
            text=items['raw_text'][idx],
            filepath=items['audio'][idx]['path'],
            audio_data=items['audio'][idx]['array'],
        )

    def __getitem__(self, index):
        items = self._dataset[index]
        if isinstance(index, slice):
            input_rows = []
            start = index.start or 0
            stop = index.stop
            step = index.step or 1
            for idx in range(0, stop - start, step):
                input_rows.append(self._to_input_row(items, idx))
            return input_rows
        else:
            return self._to_input_row(items, 0)

    def __len__(self):
        return len(self._dataset)


class LibriSpeechDataset:
    def __init__(self, data_dir: str):
        self._data_dir = data_dir
        self._dataset = self._get_transcriptions(self._get_all_files())

    def _get_transcriptions(self, files: List[str]):
        transcriptions = {}
        for filepath in files:
            if not filepath.endswith(".txt"):
                continue
            with open(filepath, "r") as file:
                for line in file:
                    trans_id, text = line.split(' ', maxsplit=1)
                    transcriptions[trans_id] = text.strip()

        dataset = []
        for filepath in files:
            if filepath.endswith(".txt"):
                continue
            filename = os.path.splitext(os.path.basename(filepath))[0]
            file_splits = filename.split("-")
            if len(file_splits) < 3:
                # skip unnecessary files
                continue
            group, section, idx = filename.split("-")
            id = f"{group}-{section}-{idx}"
            input_row = InputRow(
                audio_id=id,
                text=transcriptions[id],
                filepath=filepath,
                audio_data=[],
            )
            dataset.append(input_row)

        return dataset

    def _get_all_files(self) -> List[str]:
        files = []
        for dirpath, _, filenames in os.walk(self._data_dir):
            for filename in filenames:
                files.append(os.path.join(dirpath, filename))
        return files

    def __getitem__(self, index):
        return self._dataset[index]

    def __len__(self):
        return len(self._dataset)
