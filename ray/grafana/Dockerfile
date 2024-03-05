FROM continuumio/anaconda3 as base

RUN apt-get -qq update
RUN apt-get install -y wget adduser libfontconfig1 musl

COPY entrypoint.sh grafana.ini ./
RUN chmod +x entrypoint.sh

RUN wget --no-verbose -O grafana.tgz "https://dl.grafana.com/enterprise/release/grafana-enterprise-10.2.0.linux-amd64.tar.gz"
RUN mkdir -p /tmp/grafanadir
RUN tar -xf grafana.tgz -C /tmp/grafanadir --strip-components=1

ENTRYPOINT ["./entrypoint.sh"]
