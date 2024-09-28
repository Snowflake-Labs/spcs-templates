
DROP SERVICE IF EXISTS EMBEDDING_SERVICE;

CREATE SERVICE EMBEDDING_SERVICE
IN COMPUTE POOL EMB_COMPUTE_POOL
FROM SPECIFICATION '
spec:
  container:
  - name: main
    image: /AIVANOUDB/PUBLIC/EMBEDDINGS_REPO/embeddings_service:01
    command:
     - python
     - -u
     - src/main_service.py
     - --ip
     - 0.0.0.0
     - --port
     - 9000
    env:
      OBJC_DISABLE_INITIALIZE_FORK_SAFETY: YES
    resources:
      requests:
        nvidia.com/gpu: 1
      limits:
        nvidia.com/gpu: 1
  endpoint:
  - name: main
    port: 9000
'
WITH
MIN_INSTANCES = 1
MAX_INSTANCES = 1
EXTERNAL_ACCESS_INTEGRATIONS=(HF_EAI);


CREATE OR REPLACE FUNCTION EMBEDDING_SERVICE_FN (n VARCHAR)
  returns VARCHAR
  service=EMBEDDING_SERVICE
  endpoint='main'
  MAX_BATCH_ROWS=1024
  as '/process';