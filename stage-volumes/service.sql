create service test_service
in compute pool my_compute_pool
from specification
$$
spec:
  containers:
  - name: main-container
    image: /tutorial_db/data_schema/tutorial_repository/test_service:latest
    command:
    - /bin/bash
    args:
    - -c
    - "(ttyd -p 9090 -W bash &> /tmp/ttyd.log &);tail -f /tmp/ttyd.log"
    volumeMounts:
    - name: stage-volume
      mountPath: /mnt/stage
  volumes:
  - name: stage-volume
    source: stage
    stageConfig:
        name: "@tutorial_stage"
  endpoints:
  - name: main-endpoint
    port: 9090
    public: true
$$
;