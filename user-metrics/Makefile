# Makefile for SPCS user metrics service

VERSION=v0.0.1

build-local-grafana:
	echo 'Building grafana image'
	docker build -t grafana:spcs-$(VERSION) . -f ./grafana/Dockerfile

build-local-prometheus:
	echo 'Building prometheus image'
	docker build -t prometheus:spcs-$(VERSION) . -f ./prometheus/Dockerfile

build-local-otel:
	echo 'Building otel image'
	docker build -t otel:spcs-$(VERSION) . -f ./otel/Dockerfile

build-local-mdservice:
	echo 'Building mdservice image'
	docker build -t mdservice:spcs-$(VERSION) . -f ./mdservice/Dockerfile

check-repo-is-set:
ifndef REPO
	echo "REPO not set, use `REPO=SPCS_IMAGE_REPOSITORY`"
	exit 1
endif

build-upload-grafana: SERVICE_NAME=grafana
build-upload-grafana: build-upload-repo

build-upload-prometheus: SERVICE_NAME=prometheus
build-upload-prometheus: build-upload-repo

build-upload-mdservice: SERVICE_NAME=mdservice
build-upload-mdservice: build-upload-repo

build-upload-otel: SERVICE_NAME=otel
build-upload-otel: build-upload-repo

build-upload-repo: check-repo-is-set
	echo 'Building and uploading $(SERVICE_NAME) image to $(REPO)/spcs/$(SERVICE_NAME):$(VERSION)'
	docker build --platform=linux/amd64 . \
	-f ./$(SERVICE_NAME)/Dockerfile \
	--tag $(REPO)/spcs/$(SERVICE_NAME):$(VERSION) \
	--push --rm


build-upload-all: build-upload-grafana build-upload-prometheus build-upload-otel build-upload-mdservice

build-spec-file: check-repo-is-set
	echo 'Building spec file'
	SPCS_IMAGE_REPO=$(REPO) envsubst < metrics-service.yml.template &> metrics-service.yml

pull-upload-grafana: SERVICE_NAME=grafana
pull-upload-grafana: pull-upload-repo

pull-upload-prometheus: SERVICE_NAME=prometheus
pull-upload-prometheus: pull-upload-repo

pull-upload-mdservice: SERVICE_NAME=mdservice
pull-upload-mdservice: pull-upload-repo

pull-upload-otel: SERVICE_NAME=otel
pull-upload-otel: pull-upload-repo

pull-upload-repo: check-repo-is-set
	echo 'Pulling and uploading $(SERVICE_NAME) image to $(REPO)/spcs/prometheus:$(VERSION)'
	docker pull --platform=linux/amd64 snowflakedb/spcs-oss-$(SERVICE_NAME):$(VERSION)
	docker tag snowflakedb/spcs-oss-$(SERVICE_NAME):$(VERSION)  $(REPO)/spcs/$(SERVICE_NAME):$(VERSION)
	docker push $(REPO)/spcs/$(SERVICE_NAME):$(VERSION)

build-local-all: build-otel build-mdservice build-grafana build-prometheus

build-all: build-upload-all build-spec-file

pull-upload-all: pull-upload-otel pull-upload-mdservice pull-upload-prometheus pull-upload-grafana build-spec-file
