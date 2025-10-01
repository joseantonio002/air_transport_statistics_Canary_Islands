from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from scripts.pipeline.model_update.pipeline_models import pipeline_models
from scripts.pipeline.data_update.pipeline_tpairport import pipeline_traffic_per_airport
from scripts.pipeline.data_update.pipeline_tpterritory import pipeline_traffic_per_territory

# Default DAG arguments (applies to all tasks unless overridden)
default_args = {
    "owner": "airflow",
    "depends_on_past": False,   # Task won’t wait for previous run to succeed
    "email": ["alerts@mycompany.com"],  # For email alerts (optional)
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 1,               # How many times to retry a failed task
    "retry_delay": timedelta(minutes=10),  # Wait time before retry
}

# Define the DAG
with DAG(
    dag_id="monthly_pipeline_dag",
    default_args=default_args,
    description="Monthly data pipelines for airport, territory and models",
    schedule_interval="0 0 1 * *",  # Run at 00:00 on the 1st of every month
    start_date=datetime(2023, 1, 1),  # Catchup will backfill from here
    catchup=True,   # Will backfill past months if scheduler was down
    tags=["pipeline", "monthly"],
) as dag:

    # Define tasks
    task_airport = PythonOperator(
        task_id="traffic_per_airport",
        python_callable=pipeline_traffic_per_airport,
    )

    task_territory = PythonOperator(
        task_id="traffic_per_territory",
        python_callable=pipeline_traffic_per_territory,
    )

    task_models = PythonOperator(
        task_id="pipeline_models",
        python_callable=pipeline_models,
    )

    # Set execution order
    task_airport >> task_territory >> task_models