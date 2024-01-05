# Makefile for Golang HTTP server

# Name of the executable
TARGET = spcs-md-service

# Go commands
GO = go
GOCLEAN = $(GO) clean
GOTEST = $(GO) test
GOBUILD = $(GO) build
GORUN = $(GO) run

# Source files
SOURCES = spcs.go

all: clean build run

build:
	$(GOBUILD) -o $(TARGET) $(SOURCES)

run:
	./$(TARGET)

test:
	$(GOTEST) -v

clean:
	$(GOCLEAN)
	rm -f $(TARGET)
