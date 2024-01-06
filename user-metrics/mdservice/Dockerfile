################################
# Build Stage
################################
FROM golang:latest AS build

WORKDIR /app

COPY . .

# Build the Go binary
RUN CGO_ENABLED=0 GOOS=linux go build -o spcs .

################################
# Final Stage
################################
FROM alpine:latest

WORKDIR /app

# Copy only the necessary files from the build stage
COPY --from=build /app/spcs .
COPY --from=build /app/config.yaml .

# Expose port 8080 to the outside world
EXPOSE 8080

# Command to run the executable
CMD ["/app/spcs"]
