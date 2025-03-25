FROM nvcr.io/nvidia/pytorch:23.08-py3

WORKDIR /app

ADD . /app

RUN pip install --upgrade pip

COPY requirements.txt /app/requirements.txt
RUN pip install -r requirements.txt


ENTRYPOINT ["python", "-u", "./main.py"]
