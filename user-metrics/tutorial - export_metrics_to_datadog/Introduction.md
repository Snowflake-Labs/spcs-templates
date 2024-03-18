# Introduction

In this tutorial, you create a Snowpark Container Service using an open source image (OTel collector). The OTel collector is designed to collect, process, and export telemetry data, including metrics.

The collector supports various configurations to suit your observability needs. For this tutorial, you create an OTel configuration that defines a pipeline that collects metrics from a compute pool endpoint and exports them to datadog.

Note that Snowflake automatically creates a compute pool endpoint to emit metrics (see [Overview](https://docs.snowflake.com/LIMITEDACCESS/snowpark-container-services/compute-pool-metrics-overview#label-spcs-compute-pool-metrics-overview)). In this tutorial, you collect and process those metrics. You can process the metrics data any way you choose. In this tutorial, you export metrics to datadog.

When you create a service, you export metrics to your datadog cluster. During testing, you will login to your datadog account and view your metrics.
