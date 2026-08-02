from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class ConfigurationError(ValueError):
    """Raised when pipeline configuration is missing or invalid."""


@dataclass(frozen=True)
class PathConfig:
    data: Path
    previous_version: Path
    contracts: Path
    logs: Path
    metadata: Path
    temporary: Path


@dataclass(frozen=True)
class SourceConfig:
    api_base_url: str
    datasets: dict[str, str]


@dataclass(frozen=True)
class Config:
    project_root: Path
    source: SourceConfig
    paths: PathConfig
    retry_count: int
    request_timeout: float
    pipeline_timeout: float
    backoff_factor: float
    full_history_start_month: str
    calendar_end_month: str
    airflow_timezone: str


def _dotenv_values(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip("\"'")
    return values


def _value(name: str, dotenv: dict[str, str], default: Any) -> Any:
    return os.environ.get(name, dotenv.get(name, default))


def _required(mapping: dict[str, Any], key: str, path: str) -> Any:
    value = mapping.get(key)
    if value is None or value == "":
        raise ConfigurationError(f"missing required configuration: {path}")
    return value


def load_config() -> Config:
    config_path = PROJECT_ROOT / "config" / "config.yaml"
    if not config_path.is_file():
        raise ConfigurationError(f"configuration file not found: {config_path}")
    try:
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise ConfigurationError(f"invalid YAML in {config_path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise ConfigurationError("configuration root must be a mapping")
    dotenv = _dotenv_values(PROJECT_ROOT / ".env")
    source_raw = raw.get("source") or {}
    paths_raw = raw.get("paths") or {}
    if not isinstance(source_raw, dict) or not isinstance(paths_raw, dict):
        raise ConfigurationError("source and paths must be mappings")
    api_url = _value("PIPELINE_API_BASE_URL", dotenv, source_raw.get("api_base_url"))
    datasets = source_raw.get("datasets", {})
    if not api_url:
        raise ConfigurationError("missing required configuration: source.api_base_url")
    if not isinstance(datasets, dict):
        raise ConfigurationError("source.datasets must be a mapping")
    path_values = {}
    for key in PathConfig.__annotations__:
        configured = _required(paths_raw, key, f"paths.{key}")
        path_values[key] = (PROJECT_ROOT / configured).resolve() if not Path(configured).is_absolute() else Path(configured)
    retry_count = int(_value("PIPELINE_RETRY_COUNT", dotenv, raw.get("retry_count", 5)))
    request_timeout = float(_value("PIPELINE_REQUEST_TIMEOUT", dotenv, raw.get("request_timeout", 30)))
    pipeline_timeout = float(_value("PIPELINE_TIMEOUT", dotenv, raw.get("pipeline_timeout", 3600)))
    backoff_factor = float(_value("PIPELINE_BACKOFF_FACTOR", dotenv, raw.get("backoff_factor", 1)))
    if retry_count < 0 or request_timeout <= 0 or pipeline_timeout <= 0 or backoff_factor < 0:
        raise ConfigurationError("retry and timeout values must be valid positive values")
    return Config(
        project_root=PROJECT_ROOT,
        source=SourceConfig(str(api_url), {str(k): str(v) for k, v in datasets.items()}),
        paths=PathConfig(**path_values),
        retry_count=retry_count,
        request_timeout=request_timeout,
        pipeline_timeout=pipeline_timeout,
        backoff_factor=backoff_factor,
        full_history_start_month=str(_value("PIPELINE_FULL_HISTORY_START_MONTH", dotenv, raw.get("full_history_start_month", "2004-01"))),
        calendar_end_month=str(_value("PIPELINE_CALENDAR_END_MONTH", dotenv, raw.get("calendar_end_month", "2099-12"))),
        airflow_timezone=str(_value("PIPELINE_AIRFLOW_TIMEZONE", dotenv, raw.get("airflow_timezone", "Atlantic/Canary"))),
    )
