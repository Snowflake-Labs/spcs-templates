FROM otel/opentelemetry-collector-contrib:0.91.0

COPY ./otel/config.yaml /etc/spcs-otelcol/config.yaml

ENTRYPOINT ["/otelcol-contrib"]
CMD ["--config", "/etc/spcs-otelcol/config.yaml"]
