#!/usr/bin/env python3

import os
import subprocess
from jinja2 import Template
from typing import Optional, Tuple, Dict
from pathlib import Path

from logger import log

IMG_TAG: str = "llm-base"
BASE_IMAGE: str = f"public.ecr.aws/h9k5u5w6/aivanou-pub01:{IMG_TAG}"
PROJECT_NAME: str = "llama2-hf-chat"
COMPUTE_POOL_INSTANCE: str = "GPU_3"


def _get_std_or_none(stream) -> Optional[str]:
    if stream is None:
        return None
    else:
        return stream.decode('utf-8')


def run_cmd(cmd: str, print_output: bool = False, stdout_channel: Optional[int] = subprocess.PIPE,
            stderr_channel: Optional[int] = subprocess.PIPE) -> Tuple[Optional[str], Optional[str]]:
    cmd = cmd.split(" ")
    result = subprocess.run(cmd, stdout=stdout_channel, stderr=stderr_channel)
    stdout = _get_std_or_none(result.stdout)
    stderr = _get_std_or_none(result.stderr)
    if result.returncode != 0 or print_output:
        log.info(f"Printing output of: {cmd}, exitcode: {result.returncode}")
        log.info("================STDOUT==============")
        log.info(stdout)
        log.info("================STDERR==============")
        log.info(stderr)
        log.info(("==================================="))
    return stdout, stderr


def upload_image(source_image: str, destination_repo: str, username: str, password: str) -> str:
    run_cmd("docker logout public.ecr.aws")
    run_cmd(f"docker login {destination_repo} -u {username} -p {password}")
    run_cmd(f"docker pull {source_image}", stdout_channel=None, stderr_channel=None)
    destination_img: str = f"{destination_repo}/images:{PROJECT_NAME}"
    run_cmd(f"docker tag {source_image} {destination_img}")
    run_cmd(f"docker push {destination_img}", stdout_channel=None, stderr_channel=None)
    return destination_img


def generate_spcs_spec(spec_template_file_path: Path, image_repo: str, hf_token: str) -> str:
    with open(spec_template_file_path, 'r', encoding='utf-8') as file:
        spec_template = file.read()
    template = Template(spec_template, trim_blocks=True, keep_trailing_newline=True)
    params: Dict[str, str] = {
        "repo_image": image_repo,
        "hf_token": hf_token,
    }
    rendered_text = template.render(params)

    spec_file_path = os.path.join(spec_template_file_path.parent, spec_template_file_path.stem)
    with open(spec_file_path, 'w', encoding='utf-8') as file:
        file.write(rendered_text)
    return spec_file_path


def get_hf_token(args_hf_token: Optional[str]) -> str:
    if args_hf_token is not None:
        return args_hf_token
    elif 'HUGGING_FACE_HUB_TOKEN' in os.environ:
        return os.environ['HUGGING_FACE_HUB_TOKEN']
    else:
        raise Exception("""
No Hugging Face token found. 
1. Create HF account: https://huggingface.co 
2. Follow: https://huggingface.co/docs/hub/security-tokens to get token.
3. Follow https://ai.meta.com/resources/models-and-libraries/llama-downloads/ to request access to LLAMA2 
4. Follow https://huggingface.co/meta-llama/Llama-2-7b-hf to access hugging face model
        """)
