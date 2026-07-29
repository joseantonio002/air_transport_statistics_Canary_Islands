from pathlib import Path

import pytest

from update_data.main import AutomationError, run_automation


class Runner:
    def __init__(self, statuses=None):
        self.commands = []
        self.statuses = iter(statuses or [])

    def __call__(self, command, **kwargs):
        self.commands.append(command)
        try:
            stdout = next(self.statuses)
        except StopIteration:
            stdout = ""
        return type("Result", (), {"stdout": stdout, "returncode": 0})()


def test_dirty_worktree_fails_before_docker(tmp_path: Path) -> None:
    runner = Runner([" M file.py\n"])
    with pytest.raises(AutomationError, match="clean"):
        run_automation(tmp_path, runner=runner)
    assert len(runner.commands) == 1


def test_airflow_unavailable_has_startup_guidance(tmp_path: Path) -> None:
    runner = Runner(["", ""])
    with pytest.raises(AutomationError, match="docker compose up"):
        run_automation(tmp_path, runner=runner)


def test_success_runs_plots_commits_and_pushes(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "index.html").write_text("ok", encoding="utf-8")
    runner = Runner(["", "airflow-scheduler\n", "run-1\n", "success\n", "", "", ""])

    run_automation(tmp_path, runner=runner, required_outputs=["docs/index.html"], sleep=lambda _: None)

    assert any(command[:3] == ["git", "commit", "-m"] for command in runner.commands)
    assert ["git", "push"] in runner.commands
    commit = next(command for command in runner.commands if command[:2] == ["git", "commit"])
    assert commit[-1] == "Pipeline updated via automation script"


def test_failed_dag_stops_before_plots(tmp_path: Path) -> None:
    runner = Runner(["", "airflow-scheduler\n", "run-1\n", "failed\n"])
    with pytest.raises(AutomationError, match="failed"):
        run_automation(tmp_path, runner=runner, sleep=lambda _: None)
    assert not any("update_plots.py" in command for command in runner.commands)
