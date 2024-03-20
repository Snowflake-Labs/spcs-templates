#!/usr/bin/env python3

import hashlib
import json
import os
import sys
import time
from dataclasses import dataclass
from typing import List, Dict, Optional

import snowflake.connector
from snowflake.connector.connection import SnowflakeConnection
from snowflake.connector.cursor import SnowflakeCursor

from logger import log

IMG_TAG: str = "llm-base"
BASE_IMAGE: str = f"public.ecr.aws/h9k5u5w6/aivanou-pub01:{IMG_TAG}"
PROJECT_NAME: str = "llama2-hf-chat"
COMPUTE_POOL_INSTANCE: str = "GPU_3"


@dataclass
class ImageRepository:
    name: str
    db: str
    schema: str
    repository_url: str


@dataclass
class ComputePool:
    name: str
    state: str
    instance_family: str


@dataclass
class Container:
    status: str
    message: str
    name: str
    instanceId: str


@dataclass
class Service:
    db: str
    schema: str
    name: str
    owner: str
    compute_pool: str
    containers: List[Container]
    endpoints: Dict[str, str]


def _exec_sql(ctx: SnowflakeConnection, sql: str, log_results: bool = False) -> list[dict]:
    log.info(f"Executing: {sql}")
    output: List[SnowflakeCursor] = list(ctx.execute_string(sql))
    result = output[0].fetchall()
    if log_results:
        log.info(result)
    return result


def _get_pending_containers(service: Service) -> List[Container]:
    containers = list()
    for container in service.containers:
        if container.status.upper() == 'PENDING':
            containers.append(container)
    return containers


def get_snowflake_connection(account: str, user: str, password: str, db: str, schema: str) -> SnowflakeConnection:
    return snowflake.connector.connect(
        host=f"sfengineering-{account}.snowflakecomputing.com",
        protocol='https',
        account=account,
        user=user,
        password=password,
        database=db,
        schema=schema,
    )


class SnowHandler:

    def __init__(self, ctx: SnowflakeConnection):
        self.ctx = ctx

    def create_database(self, db: str):
        sql = f"""
    CREATE DATABASE IF NOT EXISTS {db};
        """
        _exec_sql(self.ctx, sql, log_results=True)

    def drop_compute_pool(self, compute_pool_name: str) -> None:
        try:
            stop_sql = f"""
            ALTER COMPUTE POOL {compute_pool_name} STOP ALL
            """
            _exec_sql(self.ctx, stop_sql, log_results=True)
        except Exception as e:
            log.info("Compute pool does not exist, skipping")
        drop_sql = f"""
    DROP COMPUTE POOL IF EXISTS {compute_pool_name}
        """
        _exec_sql(self.ctx, drop_sql, log_results=True)

    def drop_service(self, db: str, schema: str, service_name: str) -> None:
        sql = f"""
    DROP SERVICE IF EXISTS {db}.{schema}.{service_name}
        """
        _exec_sql(self.ctx, sql, log_results=True)

    def create_schema(self, db: str, schema: str):
        sql = f"""
    CREATE SCHEMA IF NOT EXISTS {db}.{schema};
        """
        _exec_sql(self.ctx, sql, log_results=True)

    def create_compute_pool(self, compute_pool_name: str, instance_type: str) -> None:
        sql = f"""
    CREATE COMPUTE POOL IF NOT EXISTS {compute_pool_name}
    MIN_NODES = 1
    MAX_NODES = 1
    INSTANCE_FAMILY = {instance_type}
        """
        result = _exec_sql(self.ctx, sql, log_results=True)
        statement = result[0][0]
        if 'already exists' in statement:
            compute_pool = self.get_compute_pool(compute_pool_name)
            if compute_pool.instance_family.upper() != COMPUTE_POOL_INSTANCE:
                raise Exception(f"""
    Compute pool with name: {compute_pool_name} exists with incorrect instance type.
    Expected instance type: {COMPUTE_POOL_INSTANCE}, actual type: {compute_pool.instance_family}
    Either drop compute pool or use different compute pool name
    """)

    def get_compute_pool(self, compute_pool_name: str) -> ComputePool:
        sql = f"""
    DESC COMPUTE POOL {compute_pool_name}
        """
        result = _exec_sql(self.ctx, sql)
        if len(result) == 0:
            raise Exception(f"compute pool: {compute_pool_name} not found")
        cp_data = result[0]
        return ComputePool(name=cp_data[0], state=cp_data[1], instance_family=cp_data[4])

    def wait_for_compute_pool(self, compute_pool_name: str, timeout_seconds: int = 1200) -> None:
        start_time_ms = round(time.time() * 1000)
        end_time_ms = start_time_ms + timeout_seconds * 1000
        while end_time_ms > round(time.time() * 1000):
            compute_pool = self.get_compute_pool(compute_pool_name)
            num_seconds = (round(time.time() * 1000) - start_time_ms) / 1000
            print(f"Waiting {num_seconds} seconds, current compute pool status: {compute_pool.state}", end="")
            if compute_pool.state.upper() in ['ACTIVE', 'IDLE']:
                print("")
                return
            else:
                time.sleep(10)  # wait 30 seconds
            print("\r", end="")
        status = self.get_compute_pool(compute_pool_name)
        raise Exception(
            f"Compute pool stuck in: {status}, this might be related to resource shortage. Contact SPCS oncall")

    def list_compute_pools(self):
        sql = f"""
    SHOW COMPUTE POOLS;
        """
        output: List[SnowflakeCursor] = list(self.ctx.execute_string(sql))
        if len(output) != 1:
            raise Exception("Error")
        compute_pools = output[0].fetchall()
        for compute_pool in compute_pools:
            log.info("%s - %s - %s", compute_pool[0], compute_pool[1], compute_pool[4])

    def create_stage(self, db: str, schema: str, stage_name: str):
        sql = f"""
    CREATE STAGE IF NOT EXISTS {db}.{schema}.{stage_name} ENCRYPTION = (type = 'SNOWFLAKE_SSE');
        """
        repo = self.get_repository(db, schema, stage_name)
        if repo is not None:
            raise Exception(f"""
                You have image repository with name {db}.{schema}.{stage_name}, please 
                use different name for stage.
            """)
        _exec_sql(self.ctx, sql, log_results=True)

    def upload_service_spec(self, db: str, schema: str, stage: str, spec_local_file: str) -> str:
        file_hash = hashlib.md5(open(spec_local_file, "rb").read()).hexdigest()
        spec_filename = os.path.basename(spec_local_file)
        stage_dir = os.path.join("services", file_hash)
        sql: str = f"""
    PUT file://{spec_local_file} @{db}.{schema}.{stage}/{stage_dir} auto_compress=false OVERWRITE = TRUE;
    """
        _exec_sql(self.ctx, sql, log_results=True)
        return f"{stage}/{stage_dir}/{spec_filename}"

    def get_repository(self, db: str, schema: str, repo_name: str) -> Optional[ImageRepository]:
        sql = f"""
    SHOW IMAGE REPOSITORIES;
        """
        output: List[SnowflakeCursor] = list(self.ctx.execute_string(sql))
        data = output[0].fetchall()
        for repo in data:
            curr_repo_name, curr_db, curr_schema = repo[1], repo[2], repo[3]
            if curr_repo_name.lower() == repo_name.lower() \
                    and curr_db.lower() == db.lower() \
                    and curr_schema.lower() == schema.lower():
                return ImageRepository(repo_name, db, schema, repo[4])
        return None

    def create_repository(self, db: str, schema: str, repo_name: str):
        sql = f"""
    CREATE IMAGE REPOSITORY IF NOT EXISTS {db}.{schema}.{repo_name};
        """
        _exec_sql(self.ctx, sql, log_results=True)

    def create_service(self,
                       compute_pool_name: str,
                       stage_path: str,
                       db: str,
                       schema: str,
                       service_name: str):
        sql = f"""
    CREATE SERVICE {db}.{schema}.{service_name}
      MIN_INSTANCES = 1
      MAX_INSTANCES = 1
      COMPUTE_POOL =  {compute_pool_name}
      spec=@{stage_path};
        """
        _exec_sql(self.ctx, sql, log_results=True)

    def _get_service_status(self, db: str, schema: str, name: str) -> List[Container]:
        sql = f"""
    call SYSTEM$GET_SERVICE_STATUS('{db}.{schema}.{name}')
        """
        result = _exec_sql(self.ctx, sql)
        data = json.loads(result[0][0])
        containers = list()
        for cell in data:
            containers.append(Container(name=cell['containerName'],
                                        status=cell['status'],
                                        message=cell['message'],
                                        instanceId=cell['instanceId']))
        return containers

    def get_service(self, db: str, schema: str, name: str) -> Service:
        sql = f"""
    DESC SERVICE {db}.{schema}.{name}
        """
        result = _exec_sql(self.ctx, sql)
        if len(result) == 0:
            raise Exception(f"service: {db}.{schema}.{name} not found")
        data = result[0]
        endpoints = json.loads(data[7])
        containers = self._get_service_status(db, schema, name)
        return Service(name=data[0], db=data[1], schema=data[2], owner=data[3],
                       compute_pool=data[4], containers=containers, endpoints=endpoints)

    def wait_for_service(self, db: str, schema: str, name: str,
                         timeout_seconds: int = 600) -> Service:
        start_time_ms = round(time.time() * 1000)
        end_time_ms = start_time_ms + timeout_seconds * 1000
        while end_time_ms > round(time.time() * 1000):
            service = self.get_service(db, schema, name)
            num_seconds = (round(time.time() * 1000) - start_time_ms) / 1000
            pending_containers = _get_pending_containers(service)
            print(f"Waiting {num_seconds} seconds for service to be ready. Pending containers: {pending_containers}",
                  end="")
            if len(pending_containers) == 0:
                print("")
                return service
            else:
                time.sleep(10)  # wait 30 seconds
            print("\r", end="")
        service = self.get_service(db, schema, name)
        raise Exception(
            f"Service is not ready, service: {service}. Contact SPCS oncall")

    def _get_log_batch(self, db: str, schema: str,
                       service_name: str, instance_id: str,
                       container_name: str) -> List[str]:
        sql = f"""
        CALL SYSTEM$GET_SERVICE_LOGS('{db}.{schema}.{service_name}', '{instance_id}', '{container_name}', 100);
        """
        result = _exec_sql(self.ctx, sql, log_results=False)
        if len(result[0]) != 1:
            raise Exception(f"Incorrect result: {result} for service {db}.{schema}.{service_name}")
        return result[0][0].split('\n')

    def stream_service_logs(self, db: str, schema: str, service_name: str,
                            instance_id: str, container_name: str, stop_condition_phrase: str,
                            timeout_seconds: int = 300) -> bool:
        start_time_ms = round(time.time() * 1000)
        end_time_ms = start_time_ms + timeout_seconds * 1000
        while end_time_ms > round(time.time() * 1000):
            log_batch = self._get_log_batch(db, schema, service_name, instance_id, container_name)
            for log_line in log_batch:
                log.info(log_line)
                if stop_condition_phrase.lower() in log_line.lower():
                    return True
            time.sleep(10)
            for _ in log_batch:
                sys.stdout.write("\033[F")
                sys.stdout.write("\033[K")
        return False
