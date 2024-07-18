from airflow.models import BaseOperator
from airflow.providers.snowflake.hooks.snowflake import SnowflakeHook
from airflow.utils.decorators import apply_defaults
from airflow.exceptions import AirflowException
from typing import Iterable, Mapping
import re
import yaml,json

class SPCSJobOperator(BaseOperator):
    ui_color = '#29B5E8'
    @apply_defaults
    def __init__(self,
                 image,
                 bash_command,
                 snowflake_conn_id: str = "snowflake_default",
                 compute_pool: str = 'airflow_worker_pool',
                 external_access_integrations :str | Iterable[str] = ['airflow_spcs_egress_access_integration'],
                 secrets :dict | Mapping[str,str] = None,
                 *args,
                 **kwargs):
        super().__init__(*args, **kwargs)
        self.snowflake_conn_id = snowflake_conn_id
        
        self.image = image
        self.bash_command = bash_command
        self.compute_pool = compute_pool
        self.external_access_integrations = external_access_integrations
        self.secrets = secrets
        self.generic_secret_string_flag = False
       

    def execute(self, context):

        taskId=context.get("task_instance").task_id
        task_name = re.sub(r'[^a-zA-Z0-9\s]','',taskId.lower())[:36]

        runId = context.get("task_instance").run_id
        try_number = context.get("task_instance").try_number
        run_name = re.sub(r'[^a-zA-Z0-9\s]', '',runId.replace('scheduled','s').replace('manual','m')[:-6])

        self.taskName = task_name + '_' + run_name + '_' + str(try_number)

        self.job_service = f"""
execute job service
in compute pool {self.compute_pool}
name = airflow_db.airflow_schema.{self.taskName}
external_access_integrations = ({self.get_external_access_integrations()})                                                                                                                                                                                                                                                                                                                                                                                                                                         
from specification $$
{self.generate_spec()}
$$;"""

        #Create SnowflakeHook
        hook = SnowflakeHook(snowflake_conn_id=self.snowflake_conn_id,)
            
        # Execute Service
        hook.run(self.job_service)
        
        log = hook.run(f"call system$get_service_status('airflow_db.airflow_schema.{self.taskName}')",handler = self.get_log)
        status = json.loads(log)[0]['status']
        self.log.info(f'SPCS Job: {self.taskName} ended with status: {status}')

        logs = hook.run(f"call system$get_service_logs('airflow_db.airflow_schema.{self.taskName}','0','taskcontainer')",handler = self.get_log)
        self.log.info(logs)

        if status != 'DONE':
            raise AirflowException("Task failed with exception")

    def get_external_access_integrations(self):
        
        if type(self.external_access_integrations)==list:
            return ",".join([i for i in self.external_access_integrations])
        else:
            return self.external_access_integrations
    
    def generate_spec(self):

        if self.secrets is not None:
            secrets_spec = {"secrets":self.get_secrets_spec()}

        if self.generic_secret_string_flag:
            bash_cmd = ["bash","-c","render-secrets -f $HOME; "+ self.bash_command]
        else:
            bash_cmd = ["bash","-c",self.bash_command]

        spec = {"spec":
                    {"container":[
                        {"name":"taskcontainer",
                        "image": self.image,
                        "command": bash_cmd
                        }
                        ]}
        }

        if self.secrets is not None:
            spec['spec']['container'][0].update(secrets_spec)
            
        return yaml.dump(spec).replace('\'','"')

    def get_log(self,cur):

        return_value = cur.fetchone()[0]
        self.log.info(f"Log info from container: {return_value}")

        return return_value

    def get_secrets_spec(self):

        secrets_spec = []
        for k,v in self.secrets.items():

            secrets={"snowflakeSecret":"","secretKeyRef":"","envVarName":""}
            
            name = k.split('.')[:-1]
            env =  k.split('.')[-1]

            if env == 'secret_string':
                self.generic_secret_string_flag = True
            
            secrets["snowflakeSecret"] = ".".join([s for s in name])
            secrets["secretKeyRef"] = env or ""
            secrets["envVarName"] = v or ""
            
            secrets_spec.append(secrets)
        
        return secrets_spec
