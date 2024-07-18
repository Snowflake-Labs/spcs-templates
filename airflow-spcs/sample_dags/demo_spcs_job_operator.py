import os
from datetime import timedelta,datetime
from airflow import DAG
from infra.common import airflow_slack_alerts
from snowservice.operators.snowflake import SPCSJobOperator

DEFAULT_ARGS = {
  'owner': 'demo',
  'depends_on_past': False,
  'start_date': datetime(2024, 5, 1),
  'email': ['useremail@email.com'],
  'email_on_failure': True,
  'email_on_retry': False,
  'retries': 0,
  'retry_delay': timedelta(minutes = 5),
  #'on_failure_callback': airflow_slack_alerts.task_fail_slack_alert
}

with DAG(
    dag_id="spcs_job_demo_dag",default_args=DEFAULT_ARGS,
    tags=["spcs-demo"],
    schedule="@once",
    catchup=False,
) as dag:
    

    
    run_business_process_model = SPCSJobOperator(
                            task_id='run_spcs_job', 
                            image= '/airflow_db/airflow_schema/airflow_repository/some_image:latest', 
                            bash_command = "echo 'some bash command'",
                            #secrets = {"airflow_db.airflow_schema.secret_name.password":"ENV_VARIABLE"}
                            #compute_pool = 'TESTPOOL_SNOWCAT_STANDARD_4_CPU',
                            #snowflake_conn_id = "snowhouse_test"
                            )
    