ARG BASE_IMAGE=python:3.11-slim
FROM $BASE_IMAGE
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -r requirements.txt
COPY app.py ./
EXPOSE 8080
CMD ["python3", "app.py"]
