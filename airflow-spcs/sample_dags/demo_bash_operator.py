import os
from datetime import timedelta,datetime
from airflow import DAG
#from infra.common import airflow_slack_alerts
from airflow.operators.bash_operator import BashOperator

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
    dag_id="sample_python_dag",default_args=DEFAULT_ARGS,
    tags=["spcs-demo"],
    schedule="@once",
    catchup=False,
) as dag:
    
   task_1 = BashOperator(task_id='sampleTask_bash', 
                        bash_command = "for i in {1..5}; do sleep 2; echo `date` : Hello World!; done"
                      )
   