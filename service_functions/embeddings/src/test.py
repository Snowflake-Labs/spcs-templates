import os
from typing import List
from pathlib import Path
import torch
from transformers import pipeline, AutoModelForSequenceClassification, AutoTokenizer
import transformers

model = AutoModelForSequenceClassification.from_pretrained('bhadresh-savani/distilbert-base-uncased-emotion')
tokenizer = AutoTokenizer.from_pretrained('bhadresh-savani/distilbert-base-uncased-emotion')

classifier = pipeline(
    "text-classification",
    model=model,
    tokenizer=tokenizer,
    top_k=2,
    batch_size=32)

result = classifier("I love using Hugging Face models!")
print(result)
