FROM continuumio/anaconda3 as base

WORKDIR /prom

RUN apt-get -qq update
RUN apt-get install -y wget
COPY entrypoint.sh prometheus.yml prom_metrics_service_discovery.json ./
RUN chmod +x entrypoint.sh

RUN wget --no-verbose -O prometheus.tgz "https://github.com/prometheus/prometheus/releases/download/v2.47.2/prometheus-2.47.2.linux-amd64.tar.gz"
RUN mkdir -p /tmp/prometheusdir
RUN tar -xf prometheus.tgz -C /tmp/prometheusdir --strip-components=1

ENTRYPOINT ["./entrypoint.sh"]
