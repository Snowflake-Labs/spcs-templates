from typing import List, Dict
import os
import yaml

from airflow.hooks.base_hook import BaseHook
from airflow.contrib.operators.slack_webhook_operator import SlackWebhookOperator


def task_fail_slack_alert(context):
    """
    Takes task instance as an input formates message and post it to the Slack using SlackWebhookOperator 
    """

    if "slack_channel" not in context.get("dag").default_args:
        slack_conn_id = "slack-airflow"
    else:
        slack_str = context.get("dag").default_args["slack_channel"]
        slack_conn_id = slack_str.replace("#", "slack-").replace(" ", "") or slack_conn

    print("Slack connection Id is ", slack_conn_id)

    slack_webhook_token = BaseHook.get_connection(slack_conn_id).password

    log_url = context.get("task_instance").log_url
    
    slack_msg = """
            :red_circle: Task Failed. 
            *Task*: {task}  
            *Dag*: {dag} 
            *Execution Time*: {exec_date}  
            *Log Url*: {log_url} 
            """.format(
        task=context.get("task_instance").task_id,
        dag=context.get("task_instance").dag_id,
        exec_date=context.get("execution_date"),
        log_url=log_url,
    )
    failed_alert = SlackWebhookOperator(
        task_id="slack_test",
        slack_webhook_conn_id=slack_conn_id,
        message=slack_msg,
        username="airflow",
    )
    return failed_alert.execute(context=context)
