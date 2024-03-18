# Makefile for Golang HTTP server

# Name of the executable
TARGET = spcs-mdservice

# Go commands
GO = go
GOCLEAN = $(GO) clean
GOTEST = $(GO) test
GOBUILD = $(GO) build
GORUN = $(GO) run

SOURCES = spcs.go

all: clean build run

build:
	$(GOBUILD) -o $(TARGET) .

run:
	./$(TARGET)

test:
	$(GOTEST) -v

clean:
	$(GOCLEAN)
	rm -f $(TARGET)
