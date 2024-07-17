FROM python:3.10-slim

RUN pip install snowflake-cli-labs

ADD ./airflow/git-sync /root/.config/snowflake
RUN mkdir /dags && chmod 600 /root/.config/snowflake/config.toml && chmod 755 /root/.config/snowflake/git-sync.sh
ENV HOME /root/.config/snowflake
WORKDIR $HOME
