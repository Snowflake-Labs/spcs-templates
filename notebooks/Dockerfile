ARG BASE_IMAGE=nvcr.io/nvidia/pytorch:23.08-py3

FROM ${BASE_IMAGE}

WORKDIR /app

RUN pip install --upgrade pip
COPY requirements.txt ./
RUN pip install -r ./requirements.txt

COPY entrypoint.sh ./
RUN chmod +x ./entrypoint.sh

RUN curl -LO https://github.com/tsl0922/ttyd/releases/download/1.7.7/ttyd.x86_64 \
    && mv ttyd.* /usr/local/bin/ttyd \
    && chmod +x /usr/local/bin/ttyd

ENTRYPOINT [ "./entrypoint.sh" ]