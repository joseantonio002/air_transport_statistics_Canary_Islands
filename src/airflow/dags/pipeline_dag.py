from datetime import timedelta
import os

import pendulum
from airflow import DAG
from airflow.providers.docker.operators.docker import DockerOperator
from docker.types import Mount


timezone = os.environ.get("PIPELINE_TIMEZONE", "Atlantic/Canary")
with DAG(
    dag_id="istac_air_transport_pipeline",
    schedule="0 6 5 * *",
    start_date=pendulum.datetime(2026, 1, 1, tz=timezone),
    catchup=False,
    default_args={"retries": int(os.environ.get("PIPELINE_RETRIES", "5"))},
    dagrun_timeout=timedelta(seconds=int(os.environ.get("PIPELINE_TIMEOUT", "3600"))),
) as dag:
    run_pipeline = DockerOperator(
        task_id="run_pipeline",
        image=os.environ.get("PIPELINE_IMAGE", "istac-air-transport-pipeline:latest"),
        command="python -m pipeline run",
        docker_url="unix://var/run/docker.sock",
        mount_tmp_dir=False,
        mounts=[
            Mount(source=os.environ.get("PIPELINE_DATA_DIR", "./data"), target="/opt/pipeline/data", type="bind"),
            Mount(source=os.environ.get("PIPELINE_CONFIG_DIR", "./config"), target="/opt/pipeline/config", type="bind"),
            Mount(source=os.environ.get("PIPELINE_CONTRACT_DIR", "./data_contracts"), target="/opt/pipeline/data_contracts", type="bind"),
            Mount(source=os.environ.get("PIPELINE_RUNTIME_DIR", "./runtime"), target="/opt/pipeline/runtime", type="bind"),
        ],
    )
