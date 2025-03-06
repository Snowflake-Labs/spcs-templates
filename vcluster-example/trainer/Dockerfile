FROM nvcr.io/nvidia/pytorch:23.08-py3

RUN apt-get update && apt-get upgrade -y

WORKDIR /app

ADD ./ /app

RUN pip install --upgrade pip
RUN pip install -r ./requirements.txt

ENTRYPOINT ["python", "-u", "main.py"]