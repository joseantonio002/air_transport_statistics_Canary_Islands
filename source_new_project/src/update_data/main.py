from __future__ import annotations

import subprocess
import time
from pathlib import Path
from typing import Callable


class AutomationError(RuntimeError):
    """Raised when the local visualization update cannot complete."""


def _default_runner(command: list[str], **kwargs):
    return subprocess.run(command, **kwargs)


def run_automation(
    project_root: str | Path,
    *,
    runner: Callable = _default_runner,
    sleep: Callable[[float], None] = time.sleep,
    required_outputs: list[str] | None = None,
    max_polls: int = 60,
) -> None:
    root = Path(project_root)

    def command(args: list[str]):
        result = runner(args, cwd=root, capture_output=True, text=True)
        if getattr(result, "returncode", 0) != 0:
            raise AutomationError(f"command failed: {' '.join(args)}\n{getattr(result, 'stdout', '')}")
        return getattr(result, "stdout", "")

    if command(["git", "status", "--porcelain"]).strip():
        raise AutomationError("git worktree must be clean before visualization update")
    running = command(["docker", "compose", "ps", "--services", "--filter", "status=running"])
    if not running.strip():
        raise AutomationError("Airflow is unavailable; start it with: docker compose up -d")
    trigger = command(["docker", "compose", "exec", "-T", "airflow-scheduler", "airflow", "dags", "trigger", "istac_air_transport_pipeline"]).strip()
    run_id = trigger.splitlines()[-1].strip() if trigger else ""
    if not run_id:
        raise AutomationError("Airflow did not return a DAG run ID")
    state = ""
    for _ in range(max_polls):
        state = command(["docker", "compose", "exec", "-T", "airflow-scheduler", "airflow", "dags", "state", "istac_air_transport_pipeline", run_id]).strip().lower()
        if "success" in state:
            break
        if "failed" in state or "upstream_failed" in state:
            raise AutomationError(f"Airflow DAG failed: {state}")
        sleep(5)
    else:
        raise AutomationError(f"timed out waiting for Airflow DAG: {run_id}")
    command(["python", "docs/update_plots.py"])
    for output in required_outputs or ["docs/index.html"]:
        if not (root / output).is_file():
            raise AutomationError(f"expected visualization output is missing: {output}")
    command(["git", "add", "-A"])
    command(["git", "commit", "-m", "Pipeline updated via automation script"])
    command(["git", "push"])


if __name__ == "__main__":
    run_automation(Path.cwd())
