package com.snowflake;

import com.snowflake.telemetry.trace.SnowflakeTraceIdGenerator;
import io.opentelemetry.api.OpenTelemetry;
import io.opentelemetry.sdk.autoconfigure.AutoConfiguredOpenTelemetrySdk;
import java.util.Map;

/**
 * Class provides methods to initialize and configure OpenTelemetry using {@link AutoConfiguredOpenTelemetrySdk}.
 * The AutoConfiguredOpenTelemetrySdk automatically configures the SDK using environment properties.
 * Check <a href="https://opentelemetry.io/docs/languages/java/configuration/">here</a> for more details.
 *
 * <p>AutoConfiguredOpenTelemetrySdk must be used to ensure that OpenTelemetry metrics and traces
 * are correctly tagged with the necessary resource attributes provided by Snowpark Container
 * services like spcs service name, spcs compute pool etc.
 *
 * <p>Custom SnowflakeTraceIdGenerator is configured to generate trace IDs that allow for consistency with other
 * Snowflake products.
 */
public class Configuration {

  /**
   * Initialize OpenTelemetry.
   *
   * @return a ready-to-use {@link OpenTelemetry} instance.
   */
  static OpenTelemetry initOpenTelemetry() {
    return AutoConfiguredOpenTelemetrySdk.builder()
        .addPropertiesSupplier(
            () ->
                Map.of(
                    "otel.service.name", "stock-span", // Set the service name
                    "otel.metric.export.interval",
                        "5000" // Set interval for exporting metrics to 5 seconds.
                    ))
        .addTracerProviderCustomizer(
            (tracerProviderBuilder, configProperties) -> {
              tracerProviderBuilder.setIdGenerator(SnowflakeTraceIdGenerator.INSTANCE);
              return tracerProviderBuilder;
            })
        .build()
        .getOpenTelemetrySdk();
  }
}
