from datetime import datetime, timedelta
import os

from airflow import DAG
from airflow.providers.docker.operators.docker import DockerOperator
from docker.types import Mount


with DAG(
    dag_id="istac_air_transport_pipeline",
    schedule="0 6 5 * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args={"retries": int(os.environ.get("PIPELINE_RETRIES", "5"))},
    dagrun_timeout=timedelta(seconds=int(os.environ.get("PIPELINE_TIMEOUT", "3600"))),
) as dag:
    run_pipeline = DockerOperator(
        task_id="run_pipeline",
        image=os.environ["PIPELINE_IMAGE"],
        command="python -m air_transport_statistics run-all",
        docker_url="unix://var/run/docker.sock",
        mount_tmp_dir=False,
        mounts=[
            Mount(source=os.environ["PIPELINE_DATA_DIR"], target="/app/src/data", type="bind"),
            Mount(source=os.environ["PIPELINE_CONFIG_DIR"], target="/app/src/config", type="bind"),
            Mount(source=os.environ["PIPELINE_CONTRACT_DIR"], target="/app/src/data_contracts", type="bind"),
            Mount(source=os.environ["PIPELINE_RUNTIME_DIR"], target="/app/src/runtime", type="bind"),
            Mount(source=os.environ["PIPELINE_DOCS_DIR"], target="/app/docs", type="bind"),
        ],
    )
