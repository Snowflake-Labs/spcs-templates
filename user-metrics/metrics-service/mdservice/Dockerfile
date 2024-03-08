################################
# Build Stage
################################
FROM --platform=$BUILDPLATFORM golang:latest AS build

WORKDIR /app

COPY ./mdservice .

ARG TARGETARCH

# Build the Go binary
RUN CGO_ENABLED=0 GOOS=linux GOARCH=$TARGETARCH go build -o spcs-mdservice .

################################
# Final Stage
################################
FROM alpine:latest

WORKDIR /app

# Copy only the necessary files from the build stage
COPY --from=build /app/spcs-mdservice .
COPY --from=build /app/config.yaml .

# Expose port 9003
EXPOSE 9003

# Command to run the executable
CMD ["/app/spcs-mdservice"]
