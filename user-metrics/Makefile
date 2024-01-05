# Makefile for SPCS user metrics service

build-grafana:
	docker build -t grafana:spcs-v01 . -f ./grafana/Dockerfile

build-prometheus:
	docker build -t prometheus:spcs-v01 . -f ./prometheus/Dockerfile

build-otel:
	docker build -t otel:spcs-v01 . -f ./otel/Dockerfile
