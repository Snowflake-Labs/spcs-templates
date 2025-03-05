FROM python:3.10.16-bullseye

WORKDIR /app
RUN apt-get update -y && apt-get upgrade -y && apt-get install vim -y && apt-get install dnsutils -y

RUN pip install --upgrade pip

COPY requirements.txt /app/requirements.txt
RUN pip install -r requirements.txt

ADD . /app

ENTRYPOINT ["sleep", "360000"]
