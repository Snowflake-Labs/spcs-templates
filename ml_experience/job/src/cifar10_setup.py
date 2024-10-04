import os.path
from pathlib import Path

import click
import toml
import torchvision
import torchvision.transforms as transforms
from jinja2 import Environment, FileSystemLoader


def _get_job_root_path(job_name: str):
    return Path(__file__).parent.joinpath(job_name)


def load_toml_config(job_name: str):
    return toml.load(_get_job_root_path(job_name).joinpath("config.toml"))


def _render_resource_file(input_filepath, context):
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


def _render_setup_eai_sql(filename, job_name: str, config):
    setup_resources_context = {
        'DATABASE': config['database'],
        'SCHEMA': config['schema'],
        'ROLE': config['role'],
    }
    filepath = _get_job_root_path(job_name).joinpath('resources').joinpath('input').joinpath(filename)
    return _render_resource_file(filepath, setup_resources_context)


def _render_setup_wandb_secret_sql(filename, job_name: str, config):
    setup_resources_context = {
        'DATABASE': config['database'],
        'SCHEMA': config['schema'],
        'ROLE': config['role'],
        'WANDB_SECRET': config['wandb_secret'],
    }
    filepath = _get_job_root_path(job_name).joinpath('resources').joinpath('input').joinpath(filename)
    return _render_resource_file(filepath, setup_resources_context)


def _render_spcs_spec(filename, job_name: str, config):
    setup_resources_context = {
        'CONTAINER_NAME': config['image_repo'],
        'SERVICE_INSTANCES': config['num_instances'],
        'STAGE_NAME': config['stage_name'],
    }
    filepath = _get_job_root_path(job_name).joinpath('resources').joinpath('input').joinpath(filename)
    return _render_resource_file(filepath, setup_resources_context)


@click.command()
@click.option('--wandb_secret', help="Wandb Secret")
@click.option('--image_repo', help="Image full repository path")
@click.option('--service_instances', help="Service instance number")
@click.option('--download_data', is_flag=True, help="Service instance number")
def main(wandb_secret: str, image_repo: str, service_instances: int, download_data: bool):
    job_name = "cifar10_dist_training"
    config = load_toml_config(job_name)
    setup_config = config['general']
    setup_config['wandb_secret'] = wandb_secret
    setup_config['image_repo'] = image_repo
    setup_config['num_instances'] = service_instances
    output_file = _render_setup_eai_sql('setup_eai.sql.j2', job_name, setup_config)
    print(f'Created eai output file: {output_file}')
    output_file = _render_setup_eai_sql('setup_wandb_secret.sql.j2', job_name, setup_config)
    print(f'Created wandb secret output file: {output_file}')
    output_file = _render_spcs_spec('service_spec.yaml.j2', job_name, setup_config)
    print(f'Created service spec file: {output_file}')
    if download_data:
        transform = transforms.Compose([transforms.ToTensor(), transforms.Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5))])

        torchvision.datasets.CIFAR10(root='./data', train=True, download=True,
                                     transform=transform)
        torchvision.datasets.CIFAR10(root="./data", train=False, download=True,
                                     transform=transform)


if __name__ == "__main__":
    print(f"starting setup on worker pid: {os.getpid()}")
    main()
