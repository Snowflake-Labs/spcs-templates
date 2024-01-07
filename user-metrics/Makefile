# Makefile for SPCS user metrics service

build-local-grafana:
	echo 'Building grafana image'
	docker build -t grafana:spcs-v01 . -f ./grafana/Dockerfile

build-local-prometheus:
	echo 'Building prometheus image'
	docker build -t prometheus:spcs-v01 . -f ./prometheus/Dockerfile

build-local-otel:
	echo 'Building otel image'
	docker build -t otel:spcs-v01 . -f ./otel/Dockerfile

build-local-mdservice:
	echo 'Building mdservice image'
	docker build -t mdservice:spcs-v01 . -f ./mdservice/Dockerfile

build-local-all: build-otel build-mdservice build-grafana build-prometheus

check-repo-is-set:
ifndef REPO
	echo "REPO not set, use `REPO=SPCS_IMAGE_REPOSITORY`"
	exit 1
endif

build-upload-grafana: check-repo-is-set
	echo 'Building and uploading grafana image to $(REPO)/spcs/grafana:v01'
	docker build --platform=linux/amd64 . \
	-f ./grafana/Dockerfile \
	--tag $(REPO)/spcs/grafana:v01 \
	--push --rm

build-upload-prometheus: check-repo-is-set
	echo 'Building and uploading prometheus image to $(REPO)/spcs/prometheus:v01'
	docker build --platform=linux/amd64 . \
	-f ./prometheus/Dockerfile \
	--tag $(REPO)/spcs/prometheus:v01 \
	--push --rm

build-upload-otel: check-repo-is-set
	echo 'Building and uploading otel collector image to $(REPO)/spcs/otel:v01'
	docker build --platform=linux/amd64 . \
	-f ./otel/Dockerfile \
	--tag $(REPO)/spcs/otel:v01 \
	--push --rm

build-upload-mdservice: check-repo-is-set
	echo 'Building and uploading mdservice image to $(REPO)/spcs/mdservice:v01'
	docker build --platform=linux/amd64 . \
	-f ./mdservice/Dockerfile \
	--tag $(REPO)/spcs/mdservice:v01 \
	--push --rm

build-upload-all: build-upload-grafana build-upload-prometheus build-upload-otel build-upload-mdservice

build-spec-file: check-repo-is-set
	echo 'Building spec file'
	SPCS_IMAGE_REPO=$(REPO) envsubst < metrics-service.yml.template &> metrics-service.yml

build-all: build-upload-all build-spec-file
