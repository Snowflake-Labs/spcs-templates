FROM ubuntu:22.04

WORKDIR /

USER root
RUN apt-get update \
    && apt-get install -y curl sudo vim software-properties-common wget rsync

# Install ttyd
RUN curl -LO https://github.com/tsl0922/ttyd/releases/download/1.7.7/ttyd.x86_64 \
    && mv ttyd.* /usr/local/bin/ttyd \
    && chmod +x /usr/local/bin/ttyd

RUN wget https://go.dev/dl/go1.25.1.linux-amd64.tar.gz \
    && tar -C /usr/local -xzf go1.25.1.linux-amd64.tar.gz \
    && rm go1.25.1.linux-amd64.tar.gz

ENV PATH="/usr/local/go/bin:$PATH"
COPY *.py /
