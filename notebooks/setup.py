from pathlib import Path
from jinja2 import Environment, FileSystemLoader
import click


def _render_jinja_file(input_filepath: Path, context):
    template_full_path = Path(input_filepath)
    templates_dir = str(template_full_path.parent)
    template_filename = str(template_full_path.name)
    file_loader = FileSystemLoader(templates_dir)
    env = Environment(loader=file_loader)
    template = env.get_template(template_filename)

    rendered_filepath = Path(__file__).parent.joinpath('resources').joinpath('output').joinpath(
        template_filename).with_suffix('')
    rendered_content = template.render(context)
    with open(rendered_filepath, 'w') as file:
        file.write(rendered_content)
    return rendered_filepath


def _render_service_spec(filename, config):
    setup_resources_context = {
        'IMAGE_NAME': config['image_name'],
        'NUM_GPUS': config['num_gpus'],
        'STAGE_NAME': config['stage_name'],
    }
    filepath = Path(__file__).parent.joinpath('resources').joinpath('input').joinpath(filename)
    return _render_jinja_file(filepath, setup_resources_context)


def _render_setup_eai(filename, config):
    setup_resources_context = {
        'DATABASE': config['database'],
        'SCHEMA': config['schema'],
        'EAI_NAME': config['eai_name'],
        'ROLE': config['role'],
    }
    filepath = Path(__file__).parent.joinpath('resources').joinpath('input').joinpath(filename)
    return _render_jinja_file(filepath, setup_resources_context)


def _render_stage(filename, config):
    setup_resources_context = {
        'DATABASE': config['database'],
        'SCHEMA': config['schema'],
        'ROLE': config['role'],
        'STAGE_NAME': config['stage_name'],
    }
    filepath = Path(__file__).parent.joinpath('resources').joinpath('input').joinpath(filename)
    return _render_jinja_file(filepath, setup_resources_context)


@click.group()
def cli():
    pass


@cli.command()
@click.option('--image_name', help="SPCS Image Name")
@click.option('--num_gpus', type=int, help="Number of GPUs that will be available to service")
@click.option('--stage_name', default='', help="Number of GPUs that will be available to service")
def render_spec(image_name: str, num_gpus: int, stage_name: str):
    config = {
        'image_name': image_name,
        'num_gpus': num_gpus,
        'stage_name': stage_name,
    }
    _render_service_spec('service_spec.yaml.j2', config)


@cli.command()
@click.option('--database', help="Database to store rules")
@click.option('--schema', help="Schema to store rules")
@click.option('--eai_name', help="External Access Integration name")
@click.option('--role', help="Role that will be granted usage of EAI")
def render_eai(database: str, schema: str, eai_name: str, role: str):
    config = {
        'database': database,
        'schema': schema,
        'eai_name': eai_name,
        'role': role,
    }
    _render_setup_eai('setup_eai.sql.j2', config)


@cli.command()
@click.option('--database', help="SPCS database")
@click.option('--schema', help="SPCS schema")
@click.option('--role', help="SPCS role")
@click.option('--stage_name', help="SPCS stage name")
def render_stage(database: str, schema: str, role: str, stage_name: str):
    config = {
        'database': database,
        'schema': schema,
        'role': role,
        'stage_name': stage_name,
    }
    _render_stage('setup_stage.sql.j2', config)


if __name__ == "__main__":
    cli()
