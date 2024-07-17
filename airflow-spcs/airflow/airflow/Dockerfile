FROM apache/airflow:slim-2.7.3-python3.10

ARG AIRFLOW_HOME=/opt/airflow
ARG AIRFLOW_USER_HOME_DIR=/home/airflow

USER root
RUN apt-get update && apt-get install patch
USER airflow
ARG AIRFLOW_EXTRAS="amazon,async,cncf.kubernetes,dask,docker,elasticsearch,ftp,google,google_auth,grpc,hashicorp,http,otel,microsoft.azure,odbc,pandas,pagerduty,postgres,redis,sendgrid,sftp,slack,snowflake,ssh,statsd,virtualenv"

RUN pip install "apache-airflow[${AIRFLOW_EXTRAS}]==2.7.3"
RUN pip install apache-airflow-providers-celery==3.6.0
RUN pip install --upgrade pip
ADD --chown=airflow:root ./airflow/airflow/shared /tmp/shared
# Add below file only if you are planning to put Airflow behind Okta
#ADD --chown=airflow:root ./airflow/airflow/webserver_config.py /opt/airflow/webserver_config.py
RUN pip install "/tmp/shared/infra" "/tmp/shared/snowservices" "authlib==0.15.5" "Flask-AppBuilder" "flask_admin" "shelljob" "dbt-snowflake==1.7.3"

USER 50000
