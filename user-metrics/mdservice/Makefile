# Makefile for Golang HTTP server

# Name of the executable
TARGET = simple-http-server

# Go commands
GO = go
GOCLEAN = $(GO) clean
GOTEST = $(GO) test
GOBUILD = $(GO) build

# Source files
SOURCES = main.go

all: clean build run

build:
	$(GOBUILD) -o $(TARGET) $(SOURCES)

run:
	./$(TARGET)

clean:
	$(GOCLEAN)
	rm -f $(TARGET)

