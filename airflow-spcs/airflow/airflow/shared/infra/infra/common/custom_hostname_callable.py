import os
from airflow.utils.net import get_host_ip_address

def custom_hostname_callable():
    worker_name = os.environ["WORKER_NAME"]
    use_host_name = os.environ["USE_HOSTNAME"]

    if use_host_name == 'Yes':
        return get_host_ip_address()
    
    if len(worker_name) > 5:
        return os.environ["WORKER_NAME"]
    else:
        return os.environ["SERVICE_SERVICE_HOST"]


