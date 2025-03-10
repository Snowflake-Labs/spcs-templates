FROM huggingface/transformers-torch-light
COPY main.py requirements.txt ./
COPY distilbert-base-uncased-finetuned-sst-2-english ./distilbert-base-uncased-finetuned-sst-2-english
COPY google-t5-small ./google-t5-small
RUN pip install --no-cache-dir -r requirements.txt
ENTRYPOINT ["python", "main.py"]