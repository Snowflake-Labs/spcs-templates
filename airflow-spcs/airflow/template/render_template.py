import yaml
from jinja2 import Template
import os, os.path
import re

def render_template():
    with open('values.yaml', 'r') as file:
        content = yaml.safe_load(file)

    variables = content.get('variables', {})
    template_section = content.get('template', {})

    template_str = yaml.dump(template_section)

    # Replace placeholders with variable values
    for key, value in variables.items():
        placeholder = f'{{{{ {key} }}}}'
        template_str = template_str.replace(placeholder, str(value))

    # Parse the rendered YAML to ensure it's valid
    rendered_yaml = yaml.safe_load(template_str)

    # Write the rendered YAML to the output file
    with open('rendered_values.yaml', 'w') as output_file:
        yaml.dump(rendered_yaml, output_file)

if __name__ == "__main__":

    # render values.yaml
    render_template()

    # Load the data from the YAML file
    with open('rendered_values.yaml', 'r') as data_file:
        data = yaml.safe_load(data_file)

    dirpath = os.path.normpath(os.getcwd() + os.sep + os.pardir)
    # List of template files to render
    templates = ['redis/redis.yaml.template',
                'postgres/postgres.yaml.template',
                'airflow/airflow_server.yaml.template',
                'airflow/airflow_worker.yaml.template'
                ]

    # Render each template with the data
    for template_file in templates:

        template_file = os.path.join(dirpath,template_file)
        with open(template_file, 'r') as file:
            template_content = file.read()
        
        template = Template(template_content)
        rendered_content = template.render(data)

        # Determine the output file name
        output_file = f'{os.path.splitext(template_file)[0]}'
        tmp_file = output_file+'.tmp'
        # Print or save the rendered content
        print(f'Rendered content for {template_file}:')
        #print(rendered_content)
        with open(tmp_file, 'w') as rendered_file:
            rendered_file.write(rendered_content)

        with open(tmp_file, 'r') as r, open( output_file, 'w') as o:
            for line in r:
                if line.strip():
                    o.write(line)
        if os.path.exists(tmp_file):
            os.remove(tmp_file)

        print(f'Saved rendered content to {output_file}')
