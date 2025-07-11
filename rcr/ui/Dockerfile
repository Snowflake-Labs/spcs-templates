ARG BASE_IMAGE=python:3.10-slim-buster
FROM $BASE_IMAGE
COPY chatbot.py ./
RUN pip install --upgrade pip && \
    pip install --upgrade gradio && \
    pip install --upgrade requests && \
    pip install --upgrade uvicorn && \
    pip install --upgrade fastapi 
CMD ["python3", "chatbot.py"]

