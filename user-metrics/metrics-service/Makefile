# Makefile for SPCS user metrics service

VERSION=v0.0.1

# Makefile for SPCS user metrics service

VERSION=v0.0.1

check-repo-is-set:
ifndef SNOW_REPO
	echo "SNOW_REPO environment variable is not defined."
	exit 1
endif

build-spec-file: check-repo-is-set
	echo 'Building spec file, using repository: $(SNOW_REPO)'
	SPCS_IMAGE_REPO=$(SNOW_REPO) VERSION=$(VERSION) envsubst < metrics-service.yml.template > metrics-service.yml

%.bli:
	echo 'Building $(basename $@)  image'
	docker build -t $(basename $@):spcs-$(VERSION) . -f ./$(basename $@)/Dockerfile

%.pui: check-repo-is-set
	echo 'Pulling and uploading $(basename $@) image to $(SNOW_REPO)/$(basename $@):$(VERSION)'
	docker pull --platform=linux/amd64 snowflakedb/spcs-oss-$(basename $@):$(VERSION)
	docker tag snowflakedb/spcs-oss-$(basename $@):$(VERSION)  $(SNOW_REPO)/$(basename $@):$(VERSION)
	docker push $(SNOW_REPO)/$(basename $@):$(VERSION)

%.bui: check-repo-is-set
	echo 'Building and uploading $(basename $@) image to $(SNOW_REPO)/$(basename $@):$(VERSION)'
	docker build --platform=linux/amd64 . \
	-f ./$(basename $@)/Dockerfile \
	--tag $(SNOW_REPO)/$(basename $@):$(VERSION) \
	--push --rm

images=mdservice prometheus grafana otel

build-local-images=$(addsuffix .bli, $(images))
build-local-all: $(build-local-images)

build-upload-images=$(addsuffix .bui, $(images))
build-upload-all: $(build-upload-images)

pull-upload-images=$(addsuffix .pui, $(images))
pull-upload-all: $(pull-upload-images) build-spec-file

build-all: build-upload-all build-spec-file
