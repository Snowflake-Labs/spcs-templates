from setuptools import setup, find_packages

setup(
    name='snowservice',
    author='Insert Overwrite',
    packages=find_packages(),
    install_requires=['apache-airflow==2.7.3','future','apache-airflow-providers-snowflake'],
    version='0.1',
    license='Apache License 2.0',
    description='SPCS for Airflow'
)
