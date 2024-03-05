create or replace stage ray_logs  encryption = (type = 'SNOWFLAKE_SSE');
drop stage ray_logs;

list @ray_logs;

create service rayobs
in compute pool AIVANOU01
from specification '
spec:
  containers:
  - name: grafana
    image: qa6-snowservices-ami-presubmit4.awsuswest2qa6.registry-dev.snowflakecomputing.com/testdb/public/aivanou_test01/grafana:06
    volumeMounts:
    - name: raylogs
      mountPath: /raylogs

  - name: prometheus
    image: qa6-snowservices-ami-presubmit4.awsuswest2qa6.registry-dev.snowflakecomputing.com/testdb/public/aivanou_test01/prometheus:05
    volumeMounts:
    - name: raylogs
      mountPath: /raylogs

  volumes:
  - name: raylogs
    source: "@ray_logs"

  endpoints:
  - name: grafana
    port: 3000
    public: true
  - name: prometheus
    port: 9090
    public: true
    
  networkPolicyConfig:
    allowInternetEgress: true
'
WITH 
MIN_INSTANCES = 1
MAX_INSTANCES = 1
EXTERNAL_ACCESS_INTEGRATIONS=('ALL_EAI');

create service rayhead
in compute pool AIVANOU01
from specification '
spec:
  containers:
  - name: rayhead
    image: qa6-snowservices-ami-presubmit4.awsuswest2qa6.registry-dev.snowflakecomputing.com/testdb/public/aivanou_test01/ray_head:08
    volumeMounts:
    - name: dshm
      mountPath: /dev/shm
    - name: raylogs
      mountPath: /raylogs
    env:
      RAY_GRAFANA_HOST: "http://rayobs.public.testdb.snowflakecomputing.internal:3000"
      RAY_PROMETHEUS_HOST: "http://rayobs.public.testdb.snowflakecomputing.internal:9090"

  volumes:
  - name: dshm
    source: memory
    size: 1.0Gi      
  - name: raylogs
    source: "@ray_logs"

  endpoints:
    - name: autoscaler-metrics-port
      port: 44217
      public: false
    - name: dashboard-metrics-port
      port: 44227
      public: false

    - name: ray-head
      port: 6379
      public: false
    - name: dashboard-port
      port: 8265
      public: true
    - name: object-manager-port
      port: 8076
      public: false
    - name: node-manager-port
      port: 8077
      public: false
    - name: runtime-env-agent-port
      port: 8078
      public: false
    - name: dashboard-agent-grpc-port
      port: 8079
      public: false
    - name: dashboard-grpc-port
      port: 8080
      public: false
    - name: dashboard-agent-listen-port
      port: 8081
      public: false
    - name: metrics-export-port
      port: 8082
      public: false
    - name: ray-client-server-port
      port: 10001
      public: false
    - name: min-worker-port
      port: 10002
      public: false
    - name: max-worker-port
      port: 10005
      public: false

  networkPolicyConfig:
    allowInternetEgress: true
'
WITH 
MIN_INSTANCES = 1
MAX_INSTANCES = 1
EXTERNAL_ACCESS_INTEGRATIONS=('ALL_EAI');



create service rayworker
in compute pool AIVANOU01
from specification '
spec:
  containers:
  - name: rayworker
    image: qa6-snowservices-ami-presubmit4.awsuswest2qa6.registry-dev.snowflakecomputing.com/testdb/public/aivanou_test01/rayworker:07
    volumeMounts:
    - name: dshm
      mountPath: /dev/shm
    - name: raylogs
      mountPath: /raylogs
    env:
      RAY_HEAD_ADDRESS: "rayhead.public.testdb.snowflakecomputing.internal:6379"

  endpoints:
    - name: ray-head
      port: 6379
      public: false
    - name: object-manager-port
      port: 8076
      public: false
    - name: node-manager-port
      port: 8077
      public: false
    - name: runtime-env-agent-port
      port: 8078
      public: false
    - name: dashboard-agent-grpc-port
      port: 8079
      public: false
    - name: dashboard-grpc-port
      port: 8080
      public: false
    - name: dashboard-agent-listen-port
      port: 8081
      public: false
    - name: metrics-export-port
      port: 8082
      public: false
    - name: ray-client-server-port
      port: 10001
      public: false
    - name: min-worker-port
      port: 10002
      public: false
    - name: max-worker-port
      port: 10005
      public: false
      
  volumes:
  - name: dshm
    source: memory
    size: 1.0Gi
  - name: raylogs
    source: "@ray_logs"

  networkPolicyConfig:
    allowInternetEgress: true
'
WITH 
MIN_INSTANCES = 1
MAX_INSTANCES = 1
EXTERNAL_ACCESS_INTEGRATIONS=('ALL_EAI');

drop service rayhead;
drop service rayobs;
drop service rayworker;

CALL SYSTEM$GET_SERVICE_STATUS('rayworker');
CALL SYSTEM$GET_SERVICE_LOGS('rayworker', '0', 'rayworker');

show endpoints in service rayhead;



