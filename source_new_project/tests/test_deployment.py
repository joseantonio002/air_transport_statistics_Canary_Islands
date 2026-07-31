from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_dag_uses_docker_operator_and_required_configuration() -> None:
    dag = (ROOT / "airflow" / "dags" / "pipeline_dag.py").read_text(encoding="utf-8")
    assert "DockerOperator" in dag
    assert 'command="python -m pipeline run"' in dag
    assert "catchup=False" in dag
    assert "schedule=" in dag
    for mount in ("data", "config", "data_contracts", "runtime"):
        assert mount in dag


def test_image_runs_pipeline_stages_and_init_does_not_trigger_pipeline() -> None:
    dockerfile = (ROOT / "src" / "Dockerfile").read_text(encoding="utf-8")
    assert "pip install" in dockerfile
    assert "model_update" in dockerfile
    init = (ROOT / "initialize.sh").read_text(encoding="utf-8")
    assert "PIPELINE_TIMEZONE" in init
    assert "docker compose up" in init
    assert "dags unpause" in init
    assert "dags trigger" not in init
