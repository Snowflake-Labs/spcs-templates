# Introduction

In this tutorial, you create a Snowpark Container Service using an open source image (OTel collector). The OTel collector is designed to collect, process, and export telemetry data, including metrics.

The collector supports various configurations to suit your observability needs. For this tutorial, you create an OTel configuration that defines a pipeline that collects metrics from a compute pool endpoint and exports them on an endpoint.

Note that Snowflake automatically creates a compute pool endpoint to emit metrics (see [Overview](https://docs.snowflake.com/LIMITEDACCESS/snowpark-container-services/compute-pool-metrics-overview#label-spcs-compute-pool-metrics-overview)). In this tutorial, you collect and process those metrics. You can process the metrics data any way you choose. In this tutorial, you surface the metrics to end users using a public endpoint of service you will create.

When you create a service, you expose an OTel endpoint as public to allow access to the metrics from the public web. During testing, you will use a browser to send requests to the service and review the compute pool metrics in the browser.
