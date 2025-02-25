create service SSH_SERVICE
in compute pool $COMPUTE_POOL
from specification '
spec:
  container:
  - name: main
    image: $IMAGE_URL
    command:
    - /bin/bash
    args:
    - -c
    - "(ttyd -p 9090 -W bash &> /tmp/ttyd.log &);tail -f /tmp/ttyd.log"
  endpoint:
  - name: ttyd
    port: 9090
    public: true
';
