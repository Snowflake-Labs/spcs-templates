import logging
import os, os.path, sys
import json
import click
import jinja2
import yaml
import re
from jinja2 import Environment, FileSystemLoader, select_autoescape
from jinja2 import DebugUndefined, Undefined
from jinja2.exceptions import TemplateSyntaxError

logger = logging.getLogger('infra.common')
LoggingUndefined = jinja2.make_logging_undefined(logger=logger,base=jinja2.DebugUndefined)

class SetConfig:
    def __init__(self, filename, secrets_name=None):
        self.data = {}
        self.filename = os.path.abspath(filename)
        self.templatepath = os.path.dirname(self.filename)
        self.template = os.path.basename(self.filename)
        self.targetfile = os.path.splitext(self.filename)[0]
        
        try:
            secrets_str = re.sub('\s+',' ',os.environ[secrets_name])
            secrets_params = eval(secrets_str)
        except:
            raise ValueError('Unable to retrieve secrets value from environment variable')
        
        if secrets_params:
            self.data.update(secrets_params)


    def get_template_environment(self, alternate_syntax=False):
        """
        Returns a configured Jinja template Environment instance
        """
        kwargs = {}
        if alternate_syntax:
            kwargs.update(
                block_start_string='{@',
                block_end_string='@}',
                variable_start_string='{=',
                variable_end_string='=}'
            )
        env = Environment(
            loader=FileSystemLoader(self.templatepath),
            autoescape=select_autoescape(['html', 'htm', 'xml']),
            undefined=LoggingUndefined,
            **kwargs
        )
        return env


    def render(self):
        """
        Renders the template using the input data from secrets and environment variables.
        """
        try:
            env = self.get_template_environment()
            template = env.get_template(self.template)
        except TemplateSyntaxError:
            logger.info("Template syntax error. Trying to alternate syntax: {0}".format(self.template))
            env = self.get_template_environment(alternate_syntax=True)
            template = env.get_template(self.template)
        template.stream(**self.data).dump(self.targetfile)
        logging.info("config-setter:Template render success: {0}".format(self.targetfile))

        if self.template == 'profiles.yml.template':
            fin = open(self.targetfile, "rt")
            data = fin.read()
            data = data.replace('{{', '').replace('}}','')
            fin.close()
            #open the input file in write mode
            fin = open(self.targetfile, "wt")
            fin.write(data)
            fin.close()

@click.command()
@click.option('--secrets-name', '-n', help='Snowflake serect name')
@click.option('--files_path', '-f', help='Template file path')
def config_setter(files_path, secrets_name = None):
    """
    Renders the template files from the CWD and child directories. File extension of .template is required.
    secrets_name is read from the template files.
    Generates a config file from template FILENAME in the same directory and filename
    (less the .template extension). Template values are replaced with context data retrieved
    from Snowflake secrets object.
    
    Templates should use Jinja2 formatting.  If there is a conflict with existing
    formatting in a config file, then alternate formatting can be used:
    
    Standard formatting: {{ variable }}, {% statements %}
    Alternate formatting: {= variable =}, {@ statements @}
    """
    snowflake_secrets(files_path,secrets_name)

def snowflake_secrets(files_path=os.path.dirname(os.path.realpath(sys.argv[0])),secrets_name = None):
    
    files=[]
    if files_path.endswith(".template"):
        files.append(files_path)
    else:
        for dirpath, dirnames, filenames in os.walk(files_path):
            for filename in [f for f in filenames if f.endswith(".template")]:
                files.append(os.path.join(dirpath, filename))

    for filename in files:
        secrets_name = get_secret_name(filename)
        cf = SetConfig(filename, secrets_name)
        cf.render()
    
def get_secret_name(filename):

    yml_types = ['.yml','.yaml']
    json_type = ['.json']
    secret_key = 'secretKeyName'

    ext = os.path.splitext(filename)[1]
    if ext != '.template':
        raise ValueError("Invalid file extension {0}".format(filename))
        
    if not os.path.exists(filename):
        raise FileNotFoundError("Template file not found: {0}".format(filename))

    #Get file type .yml .yaml or .json
    file_type = os.path.splitext(os.path.splitext(os.path.basename(filename))[0])[1]

    if file_type in yml_types:
        with open(filename, 'rt') as d:
            data = d.read().replace('{{', 'yyyy').replace('}}','zzzz')
        secret_key_name = yaml.load(data,Loader=yaml.FullLoader)[secret_key]
    elif file_type in json_type:
        secret_key_name = json.loads(open(filename).read())[secret_key]
    else:
        with open(filename, 'r') as read_obj:
            for line in read_obj:
                key_name = re.sub('[^A-Za-z]+', '', line.split(':')[0])
                if key_name == secret_key:
                    secret_key_name = re.sub('[^A-Za-z_-]+', '', line.split(':')[1])
        
    
    if secret_key_name is None or secret_key_name == '':
        raise ValueError("Key 'secretKeyName' not found in config file {0}".format(filename))
    else:
        return secret_key_name
