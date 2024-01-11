# Makefile for SPCS user metrics service

VERSION=v0.0.1

check-repo-is-set:
ifndef REPO
        echo "REPO not set, use `REPO=SPCS_IMAGE_REPOSITORY`"
        exit 1
endif

build-spec-file: check-repo-is-set
        echo 'Building spec file'
        $(eval SNOW_REPO:=$(shell export REPO=$(REPO); echo /$${REPO#*\/}))
        export SPCS_IMAGE_REPO=$(SNOW_REPO) export VERSION=$(VERSION); envsubst '$${SPCS_IMAGE_REPO} $${VERSION}' < metrics-service.yml.template > metrics-service.yml 2>&1
        cat metrics-service.yml

%.bli:
        echo 'Building $(basename $@)  image'
        docker build -t $(basename $@):spcs-$(VERSION) . -f ./$(basename $@)/Dockerfile

%.pui: check-repo-is-set
        echo 'Pulling and uploading $(basename $@) image to $(REPO)/$(basename $@):$(VERSION)'
        docker pull --platform=linux/amd64 snowflakedb-oss-$(basename $@):$(VERSION)
        docker tag snowflakedb-oss-$(basename $@):$(VERSION)  $(REPO)/$(basename $@):$(VERSION)
        docker push $(REPO)/$(basename $@):$(VERSION)

%.bui: check-repo-is-set
        echo 'Building and uploading $(basename $@) image to $(REPO)/$(basename $@):$(VERSION)'
        docker build --platform=linux/amd64 . \
        -f ./$(basename $@)/Dockerfile \
        --tag $(REPO)/$(basename $@):$(VERSION) \
        --push --rm

images=mdservice prometheus grafana otel

build-local-images=$(addsuffix .bli, $(images))
build-local-all: $(build-local-images) build-spec-file

build-upload-images=$(addsuffix .bui, $(images))
build-upload-all: $(build-upload-images)

pull-upload-images=$(addsuffix .pui, $(images))
pull-upload-all: $(pull-upload-images) build-spec-file

build-all: build-upload-all build-spec-file
