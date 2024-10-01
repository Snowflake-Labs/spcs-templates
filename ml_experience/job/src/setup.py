import argparse
import os.path
from pathlib import Path

import toml
from jinja2 import Environment, FileSystemLoader


def _get_job_root_path(job_name: str):
    return Path(__file__).parent.joinpath(job_name)


def load_toml_config(job_name: str):
    return toml.load(_get_job_root_path(job_name).joinpath("config.toml"))


def _render_sql_file(input_filepath, context):
    template_full_path = Path(input_filepath)
    templates_dir = str(template_full_path.parent)
    template_filename = str(template_full_path.name)
    file_loader = FileSystemLoader(templates_dir)
    env = Environment(loader=file_loader)
    template = env.get_template(template_filename)

    rendered_filepath = template_full_path.parent.parent.joinpath('output').joinpath(template_filename).with_suffix('')
    rendered_content = template.render(context)
    with open(rendered_filepath, 'w') as file:
        file.write(rendered_content)
    return rendered_filepath


def _render_setup_resources_sql(filename, job_name: str, config):
    setup_resources_context = {
        'DATABASE': config['database'],
        'SCHEMA': config['schema'],
        'ROLE': config['role'],
    }
    filepath = _get_job_root_path(job_name).joinpath('sql').joinpath('input').joinpath(filename)
    return _render_sql_file(filepath, setup_resources_context)


def main():
    parser = argparse.ArgumentParser(description="SPCS Cifar10 setup")
    parser.add_argument('job_name', type=str, help='Job Name')
    args = parser.parse_args()
    config = load_toml_config(args.job_name)
    setup_config = config['general']
    output_file = _render_setup_resources_sql('setup_eai.sql.j2', args.job_name, setup_config)
    print(f'Created output file: {output_file}')


if __name__ == "__main__":
    print(f"starting setup on worker pid: {os.getpid()}")
    main()
