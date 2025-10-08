from airflow import DAG
from airflow.providers.standard.operators.bash import BashOperator
from datetime import datetime

with DAG(
    dag_id="test_commit_dag",
    start_date=datetime(2024, 1, 1),
    schedule=None,
    catchup=False,
    tags=["test"],
    template_searchpath=None,  # Disable template file searching
) as dag:

    run_commit_script = BashOperator(
        task_id="run_commit_script",
        bash_command="""
            cd /home/jose/air_transport_statistics_Canary_Islands
            git add . && git commit -m "Test commit with airflow"
            git push
        """,
    )