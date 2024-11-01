## Running Jupyter notebooks on SPCS

### Prerequisites

In order to run this tutorial one needs the following:

* Docker, preferably version `Docker version 27.2.0, build 3ab4256`. Docker install can be
  found [here](https://docs.docker.com/engine/install/)
* Snowflake Account and User with the following
  permissions: https://github.com/Snowflake-Labs/spcs-templates/blob/main/service_functions/embeddings/sql/permissions.sql
* python 3.10
* Snowflake warehouse, database and schema should be created, and user should have access that is defined in the file
  above
* Set up some important environment variables:

```bash
export DATABASE=$MY_DATABASE
export SCHEMA=$MY_SCHEMA
export ROLE=$MY_ROLE
# External access integration, only necessary if you need access to the internet
export EAI_NAME=$MY_EAI_NAME
```

### Install

Run requirements install:

```bash
pip install -r requirements-setup.txt
```

The command above among others will install [SnowCLI](https://github.com/snowflakedb/snowflake-cli).

### Setting up EAI(External access integration) - Only if you need access to the Internet

By default, SPCS Service will not have outside access(Egress). In order to enable it, the External Access Integration(
EAI)
needs to be created. If the service does not need Egress, this section can be ignored.

Run the following cmd to create EAI SQL:

```bash
python setup.py render-eai --database $DATABASE --schema $SCHEMA --eai_name $EAI_NAME --role $ROLE
```

Run the file in the `resources/output/setup_eai.sql` using the user that can use `ACCOUNTADMIN` role.

### Setting up snowflake connection

Add a new connection to the snow cli:

```bash
snow connection add
```

The command above will start a wizard. Enter the fields using the below hints.
Skip the fields that do not have any values:

```
Name for this connection: demo_connection
Snowflake account name: <<YOUR_ACCOUNT_NAME>>
Snowflake username: <<YOUR_USER_NAME>>
Snowflake password [optional]: <<YOUR_PASSWORD>>
Role for the connection [optional]: <<YOUR_USER_ROLE>>
Warehouse for the connection [optional]: <<YOUR_WAREHOUSE>>
Database for the connection [optional]: <<YOUR_DATABASE>>
Schema for the connection [optional]: <<YOURSCHEMA>>
Connection host [optional]:
Connection port [optional]:
Snowflake region [optional]:
Authentication method [optional]:
Path to private key file [optional]:
Path to token file [optional]:
```

Set created connection as default connection:

```bash
snow connection set-default demo_connection
```

### Creating compute pool

The first step is to create compute pool.
To create GPU compute pool use this command:

```bash
snow spcs compute-pool create DEMO_GPU --family GPU_NV_S --min-nodes 1 --max-nodes 1 --no-auto-resume --auto-suspend-secs 2000
export COMPUTE_POOL=DEMO_GPU
```

To create CPU compute pool use this:

```bash
snow spcs compute-pool create DEMO_CPU --family CPU_X64_M --min-nodes 1 --max-nodes 1 --no-auto-resume --auto-suspend-secs 2000
export COMPUTE_POOL=DEMO_CPU
```

Run the following command to retrieve compute pool status:

```bash
snow spcs compute-pool status $COMPUTE_POOL
```

The expected output should look like this:

```commandline
+----------------------------------------------------------------------------------------------------------------+
| key                            | value                                                                         |
|--------------------------------+-------------------------------------------------------------------------------|
| SYSTEM$GET_COMPUTE_POOL_STATUS | {"status":"STARTING","message":"Compute pool is starting for last 1 minutes"} |
+----------------------------------------------------------------------------------------------------------------+
```

This means that compute pool is in starting. Wait for output to look like this:

```commandline
+-----------------------------------------------------------------+
| key                            | value                          |
|--------------------------------+--------------------------------|
| SYSTEM$GET_COMPUTE_POOL_STATUS | {"status":"IDLE","message":""} |
+-----------------------------------------------------------------+
```

### Preparing image

The next step is to prepare image. For this we will be using docker and snowflake image repository.

First, create image repository:

```bash
snow spcs image-repository create DEMO_REPO
```

Lets retrieve the url and remember it:

```bash
snow spcs image-repository url DEMO_REPO

export IMAGE_REPO_URL=$(snow spcs image-repository url DEMO_REPO)

echo $IMAGE_REPO_URL
```

Using your user and password that were used to create snow connection, lets push the image:

```bash
docker login $IMAGE_REPO_URL -u $USER -p $PASSWORD

docker build --platform linux/amd64  -t $IMAGE_REPO_URL/notebooks:01 . && docker push $IMAGE_REPO_URL/notebooks:01
```

### Launching service

SPCS service requires specification to be created, which is a yaml file that defines the service body.

To render service specification for GPU service, run this:

```bash
python setup.py render-spec --image_name $IMAGE_REPO_URL/notebooks:01 --num_gpus 1
```

To render service specification for CPU service:

```bash
python setup.py render-spec --image_name $IMAGE_REPO_URL/notebooks:01 --num_gpus 0
```

To launch service:

```bash
snow spcs service create demo_notebook_service --compute-pool $COMPUTE_POOL --spec-path ./resources/output/service_spec.yaml --min-instances 1 --max-instances 1 --no-auto-resume
```

The command below provides a service status. Service is ready when it is in Running state:

```bash
snow spcs service status demo_notebook_service --format json
```

Expected output is similar to this:

```bash
[
    {
        "status": "READY",
        "message": "Running",
        "containerName": "main",
        "instanceId": "0",
        "serviceName": "DEMO_NOTEBOOK_SERVICE",
        "image": "<<IMAGE>>",
        "restartCount": 0,
        "startTime": "****"
    }
]
```

Lets retrieve service logs to make sure it works:

```bash
snow spcs service logs demo_notebook_service --container-name main --instance-id 0
```

The following command retrieves SSH and Jupyter endpoints:

```bash
snow spcs service list-endpoints demo_notebook_service
```

### Persistence

SPCS supports stage mounting for storing Jupyter notebooks.

```bash
export STAGE_NAME="<<YOUR_STAGE_NAME>>"
python setup.py render-stage --database <<DB>> --schema <<SCHEMA>> --role <<ROLE>> --stage_name $STAGE_NAME
```

Render service spec with stage:

```bash
python setup.py render-spec --image_name $IMAGE_REPO_URL/notebooks:01 --num_gpus 1 --stage_name $STAGE_NAME
```

Start service with new specification:

```bash
snow spcs service create demo_notebook_service --compute-pool $COMPUTE_POOL --spec-path ./resources/output/service_spec.yaml --min-instances 1 --max-instances 1 --no-auto-resume
```

### Secrets support

Snowflake and SPCS support secrets that can be used to store credentials, e.g. AWS keys.

In order to create secret, execute the following SQL:

```sql
CREATE SECRET MY_SECRET
  TYPE = GENERIC_STRING
  SECRET_STRING = <<YOUR_STRING>>';
```

SPCS Spec supports secrets on container level:

```yaml
  containers:
    - name: "main"
      secrets:
        - snowflakeSecret:
            objectName: MY_SECRET
          envVarName: MY_SECRET
          secretKeyRef: secret_string
```

The secret above will be injected to the container under environment variable `MY_SECRET`.

One can also generate spec using `setup.py` util:

```bash
python setup.py render-spec --image_name $IMAGE_REPO_URL/notebooks:01 --num_gpus 1 --secrets SECRET1,SECRET2
```

When SPCS container starts execution, the secrets will be available in corresponding environment variables.
They can be fetched for example by this code:

```python
import os

print(os.environ['MY_SECRET'])
```

```bash
snow spcs service drop demo_notebook_service
```

### Cleanup

```bash
snow spcs service drop demo_notebook_service
```