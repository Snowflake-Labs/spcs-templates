FROM golang:1.24-alpine AS build

# Set the working directory
WORKDIR /workspace

# Copy application files to the container
COPY app.go ./
COPY go.mod go.sum ./

# Download dependencies and build the application
RUN go mod download
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -o /app app.go

# Copy to new image and run
FROM alpine
COPY stock-snap.json ./
COPY --from=build /app /app
ENTRYPOINT [ "/app" ]
