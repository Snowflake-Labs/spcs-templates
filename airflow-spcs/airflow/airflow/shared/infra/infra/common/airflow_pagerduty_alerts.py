from airflow.models import BaseOperator
from airflow.utils.decorators import apply_defaults
from airflow.providers.pagerduty.hooks.pagerduty_events import PagerdutyEventsHook
from . import airflow_slack_alerts

class PagerdutyAlertOperator(BaseOperator):
    """
    Trigger pagerduty alert if dag failed.
    """
    @apply_defaults
    def __init__(
        self,
        *,
        pagerduty_conn_id: str, 
        action:str,       
        summary:str,
        severity:str,
        source:str,
        dedup_key:str,
        links:list,
        **kwargs
        ) -> None:
        super().__init__(**kwargs)
        self.pagerduty_events_conn_id = pagerduty_conn_id
        self.action = action
        self.summary = summary
        self.severity = severity
        self.source = source
        self.dedup_key = dedup_key
        self.links = links

    def execute(self) -> None:
        """Call the PagerdutyHook to send alerts"""
        self.hook = PagerdutyEventsHook(
            pagerduty_events_conn_id = self.pagerduty_events_conn_id
        )

        self.hook.create_event(
            summary = self.summary,
            severity = self.severity,
            action = self.action,
            source = self.source,
            dedup_key = self.dedup_key,
            links = self.links
        )

class PagerDutyAlert:
    """
        Pagerduty class for sending alert
    """

    def __init__(self,context):
        
        self.page_key = """{dag}.{task}.{exec_date}""".format(
        dag=context.get("task_instance").dag_id,
        task=context.get("task_instance").task_id,
        exec_date=context.get("execution_date")
        )
        self.log_url = context.get("task_instance").log_url

        # Checking if user have specified pagerduty config dict in default args
        if 'pagerduty_config' not in context.get('dag').default_args:
            config = dict()
        else:
            config = context.get('dag').default_args['pagerduty_config']    

        # Getting service name to be alerted
        if "pagerduty_service_name" not in context.get('dag').default_args and "service_name" not in config:
            self.pagerduty_conn_id = ''   #default
        else:
            if "pagerduty_service_name" in context.get('dag').default_args:
                self.pagerduty_conn_id = context.get('dag').default_args['pagerduty_service_name'] #user_specified
            else:
                self.pagerduty_conn_id = config['service_name'] #user_specified

        if "pagerduty_severity" not in context.get('dag').default_args and "severity" not in config:
            self.severity = 'error'   #default
        else:
            if "pagerduty_severity" in context.get('dag').default_args:
                self.severity = context.get('dag').default_args['pagerduty_severity'] 
            else:
                self.severity = config['severity']
            
        if "pagerduty_dedup_key" not in context.get('dag').default_args and "dedup_key" not in config:
            self.dedup_key = self.page_key   #default
        else:
            if "pagerduty_dedup_key" in context.get('dag').default_args:
                self.dedup_key = context.get('dag').default_args['pagerduty_dedup_key'] 
            else:
                self.dedup_key = config['dedup_key']
            
        print("Pagerduty Alerting Service :",self.pagerduty_conn_id)
        print("Pagerduty Alerting Severity :",self.severity)
        print("Pagerduty Alerting Dedup_key :",self.dedup_key)
        

    def trigger_failure_alert(self):
        """
            Trigger failure alert(trigger) to pagerduty service
        """
        
        failed_alert = PagerdutyAlertOperator(
            task_id = 'pagerduty_fail_alert',
            pagerduty_conn_id = self.pagerduty_conn_id,
            action = 'trigger',
            summary = f'Airflow Task Failed - {self.page_key}',
            severity = self.severity,
            source = 'Airflow',
            dedup_key = self.dedup_key,
            links = [ { "href": self.log_url, "text": "Airflow log file" } ]
            )
        return failed_alert.execute()

    def trigger_success_alert(self):
        """
            Trigger success alert(resolve) to pagerduty service
        """
        
        success_alert = PagerdutyAlertOperator(
            task_id = 'pagerduty_success_alert',
            pagerduty_conn_id = self.pagerduty_conn_id,
            action = 'resolve',
            summary = f'Airflow Task Successful - {self.page_key}',
            severity = self.severity,
            source = 'Airflow',
            dedup_key = self.dedup_key,
            links = [ { "href": self.log_url, "text": "Airflow log file" } ]
            )
        return success_alert.execute()

# on_failure_callback function
def task_fail_pagerduty_alert(context):
    PagerDutyAlert(context).trigger_failure_alert()
    airflow_slack_alerts.task_fail_slack_alert(context) # slack alerting

# on_success_callback function
def task_success_pagerduty_alert(context):    
    PagerDutyAlert(context).trigger_success_alert()
