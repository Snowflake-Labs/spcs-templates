create service benchmark_service
in compute pool my_compute_pool
from specification
$$
spec:
  containers:
  - name: main-container
    image: /tutorial_db/data_schema/tutorial_repository/benchmark_service:latest
    command:
    - /bin/bash
    args:
    - -c
    - "(ttyd -p 9090 -W bash &> /tmp/ttyd.log &);tail -f /tmp/ttyd.log"
    volumeMounts:
    - name: stage-volume-1
      mountPath: /mnt/stage1
    - name: stage-volume-2
      mountPath: /mnt/stage2
    - name: block-1
      mountPath: /mnt/block1
  volumes:
  - name: stage-volume-1
    source: stage
    stageConfig:
        name: "@tutorial_stage"
  - name: stage-volume-2
    source: stage
    stageConfig:
        name: "@tutorial_stage"
  - name: block-1
    source: block
    size: 1000Gi
    blockConfig:
        iops: 10000
        throughput: 1000
  endpoints:
  - name: main-endpoint
    port: 9090
    public: true
$$
external_access_integrations = (allow_all_eai)
;