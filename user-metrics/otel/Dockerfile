FROM otel/opentelemetry-collector-contrib:0.91.0

COPY ./otel/config.yaml /etc/spcs-otelcol/config.yaml

ENTRYPOINT ["/spcs-otelcol"]
CMD ["--config", "/etc/spcs-otelcol/config.yaml"]
