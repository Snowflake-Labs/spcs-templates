FROM ubuntu:22.04

WORKDIR /

USER root
RUN apt-get update \
    && apt-get install -y curl sudo

# Install ttyd
RUN curl -LO https://github.com/tsl0922/ttyd/releases/download/1.7.7/ttyd.x86_64 \
    && mv ttyd.* /usr/local/bin/ttyd \
    && chmod +x /usr/local/bin/ttyd
