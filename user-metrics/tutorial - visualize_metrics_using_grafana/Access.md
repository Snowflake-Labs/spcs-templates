# 3: Access the compute pool metrics

The metrics service exposes a public endpoint named “grafana” (see the inline specification in CREATE SERVICE command). Therefore, you can log in to a web UI the service exposes to the internet, and then send requests to the service from a web browser. In this tutorial, the service respond by showing a sample pre-configured visualization of the compute pool metrics.

1. Find the URL of the public grafana UI endpoint:

```commandline
SHOW ENDPOINTS IN SERVICE metrics_visualizer;
```

2. Copy the ingress_url of the grafana endpoint and paste it in a browser tab to access the grafana endpoint. In response, the service returns a pre-configured visualization showing compute pool metrics.