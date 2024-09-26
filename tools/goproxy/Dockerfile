FROM golang:1.21 as build
WORKDIR /goproxy
ADD . /goproxy
RUN CGO_ENABLED=0 go build -o /bin/goproxy .

FROM scratch
COPY --from=build /bin/goproxy /bin/goproxy
ENTRYPOINT [ "/bin/goproxy", "-target", "http://localhost:9000", "-port", "9001", "-requests", "4"]