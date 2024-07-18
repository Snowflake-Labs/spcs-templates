from setuptools import setup, find_packages


def readme():
    with open("README.txt") as f:
        return f.read()


setup(
    name="infra",
    version="0.0.1",
    description="Snowflake Labs",
    # url='http://github.com/storborg/funniest',
    license="Snowflake internal use",
    packages=find_packages(),
    long_description=readme(),
    install_requires=[
        "Click",
        "pyyaml",
        "jinja2",
        "requests",
        "markupsafe==2.1.3",
        "apache-airflow==2.7.3"
        ],
        entry_points={
        "console_scripts": [
            "render-secrets = infra.common.vault:config_setter"
        ]
        },
    zip_safe=False,
)

