from pathlib import Path

import pytest

from pipeline.config import ConfigurationError, load_config


def write_config(root: Path, text: str) -> None:
    (root / "config" / "config.yaml").write_text(text, encoding="utf-8")


def test_loads_defaults_and_resolves_paths(project_root: Path) -> None:
    write_config(
        project_root,
        """
source:
  api_base_url: https://example.test
  datasets: {airport_passengers: C00017A_000001}
paths:
  data: data
  contracts: data_contracts
  logs: runtime/logs
  metadata: runtime/run_metadata
  temporary: runtime/tmp
""",
    )

    config = load_config(project_root)

    assert config.source.api_base_url == "https://example.test"
    assert config.source.datasets["airport_passengers"] == "C00017A_000001"
    assert config.retry_count == 5
    assert config.full_history_start_month == "2004-01"
    assert config.calendar_end_month == "2099-12"
    assert config.paths.data == project_root / "data"
    assert config.paths.metadata == project_root / "runtime/run_metadata"


def test_environment_overrides_and_dotenv(project_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    write_config(
        project_root,
        """
source: {api_base_url: https://config.test, datasets: {}}
paths: {data: data, contracts: data_contracts, logs: logs, metadata: metadata, temporary: tmp}
retry_count: 5
""",
    )
    (project_root / ".env").write_text("PIPELINE_REQUEST_TIMEOUT=31\n", encoding="utf-8")
    monkeypatch.setenv("PIPELINE_RETRY_COUNT", "7")

    config = load_config(project_root)

    assert config.retry_count == 7
    assert config.request_timeout == 31.0


def test_rejects_invalid_required_values(project_root: Path) -> None:
    write_config(
        project_root,
        """
source: {api_base_url: '', datasets: {}}
paths: {data: data, contracts: data_contracts, logs: logs, metadata: metadata, temporary: tmp}
""",
    )

    with pytest.raises(ConfigurationError, match="source.api_base_url"):
        load_config(project_root)
