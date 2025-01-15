package com.snowflake;

import com.snowflake.telemetry.trace.SnowflakeTraceIdGenerator;
import io.opentelemetry.api.OpenTelemetry;
import io.opentelemetry.sdk.autoconfigure.AutoConfiguredOpenTelemetrySdk;
import java.util.Map;

/**
 * Class provides methods to initialize and configure OpenTelemetry for the application.
 */
public class Configuration {

  /**
   * Initialize OpenTelemetry.
   *
   * @return a ready-to-use {@link OpenTelemetry} instance.
   */
  static OpenTelemetry initOpenTelemetry() {
    // The AutoConfiguredOpenTelemetrySdk automatically configures the SDK using environment properties.
    // Check https://opentelemetry.io/docs/languages/java/configuration/ for more details.
    // AutoConfiguredOpenTelemetrySdk must be used to ensure that OpenTelemetry metrics and traces are correctly tagged
    // with the necessary resource attributes provided by Snowpark Container services like spcs service name, spcs compute pool etc.
    return AutoConfiguredOpenTelemetrySdk.builder()
        .addPropertiesSupplier(() ->
                Map.of(
                    "otel.service.name", "stock-span", // Set the service name
                    "otel.metric.export.interval", "5000" // Set interval for exporting metrics to 5 seconds.
                    ))
        .addTracerProviderCustomizer(
            (tracerProviderBuilder, configProperties) -> {
              // SnowflakeTraceIdGenerator generates trace IDs incorporating a timestamp component to ensure both
              // uniqueness and traceability. Generated trace ID consists of a leading section derived from the timestamp
              // and a trailing section composed of a random suffix.
              // Using this generator is required for Snowflake to display traces & spans in Snowsight UI.
              tracerProviderBuilder.setIdGenerator(SnowflakeTraceIdGenerator.INSTANCE);
              return tracerProviderBuilder;
            })
        .build()
        .getOpenTelemetrySdk();
  }
}
