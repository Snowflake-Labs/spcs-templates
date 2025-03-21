FROM nvcr.io/nvidia/pytorch:25.02-py3

WORKDIR /app

RUN apt-get update && apt-get upgrade -y \
    && apt-get -qq install --no-install-recommends ffmpeg

COPY ./requirements.txt /app

RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

ADD ./ /app

ENTRYPOINT ["python", "-u", "./main.py"]
