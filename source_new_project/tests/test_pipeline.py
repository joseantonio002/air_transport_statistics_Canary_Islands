import csv
import json
from pathlib import Path

import pytest

import pipeline.__main__ as cli
from pipeline.pipeline import PipelineError, atomic_replace_facts, inclusive_months, run_pipeline
from pipeline.orchestrator import PipelineApplication


def rows(months, value=1):
    return [{"MonthId": month, "Value": value} for month in months]


def test_inclusive_months_and_atomic_replacement(tmp_path: Path) -> None:
    assert inclusive_months("2026-01", "2026-03") == [202601, 202602, 202603]
    atomic_replace_facts(tmp_path, rows([202601]), rows([202601]), rows([202602]), rows([202602]))
    assert "202602" in (tmp_path / "TrafficPerAirport.csv").read_text()
    assert "202601" not in (tmp_path / "TrafficPerAirport.csv").read_text()


def test_atomic_replacement_rolls_back_both_tables(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    atomic_replace_facts(tmp_path, rows([202601]), rows([202601]), rows([202602]), rows([202602]))
    original_airport = (tmp_path / "TrafficPerAirport.csv").read_bytes()
    original_territory = (tmp_path / "TrafficPerTerritory.csv").read_bytes()
    real_replace = __import__("os").replace
    calls = 0

    def fail_second(source, destination):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("replacement failed")
        return real_replace(source, destination)

    monkeypatch.setattr("pipeline.pipeline.os.replace", fail_second)
    with pytest.raises(PipelineError, match="atomic"):
        atomic_replace_facts(tmp_path, rows([202601]), rows([202601]), rows([202603]), rows([202603]))
    assert (tmp_path / "TrafficPerAirport.csv").read_bytes() == original_airport
    assert (tmp_path / "TrafficPerTerritory.csv").read_bytes() == original_territory


def test_run_writes_metadata_and_calls_model_after_both_tables(tmp_path: Path) -> None:
    calls = []

    def build(month):
        return rows([month]), rows([month])

    (tmp_path / "data").mkdir()
    run_pipeline(tmp_path / "data", "run", build, latest_month="2026-01", model_update=lambda: calls.append("model"))
    metadata = list((tmp_path / "runtime" / "run_metadata").glob("*.json"))
    document = json.loads(metadata[0].read_text())
    assert document["status"] == "success"
    assert document["mode"] == "run"
    assert calls == ["model"]


def test_cli_dispatches_run_to_real_orchestrator(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = []
    monkeypatch.setattr(cli, "run_from_project_root", lambda root, mode, **kwargs: calls.append((root, mode, kwargs)) or {})

    assert cli.main(["run", "--month", "2026-06", "--project-root", "/tmp/project"]) == 0
    assert calls == [("/tmp/project", "run", {"month": "2026-06"})]


def test_application_builds_both_fact_tables_from_extracted_groups() -> None:
    app = object.__new__(PipelineApplication)
    app.airports = {"ES_GCTS": 1}
    app.services = {"PAX": 10}
    app.movements = {"ARR": 20}
    app.territories = {"ES": 1}
    airport_row = {"SERVICIO_AEREO_CODE": "PAX", "MOVIMIENTO_AERONAVE_CODE": "ARR", "AEROPUERTO_BASE_CODE": "ES_GCTS", "AEROPUERTO_ESCALA_CODE": "ES_GCTS", "OBS_VALUE": "2"}
    territory_row = {"TERRITORIO_CODE": "ES", "AEROPUERTO_ESCALA_CODE": "ES", "SERVICIO_AEREO_CODE": "PAX", "MOVIMIENTO_AERONAVE_CODE": "ARR", "OBS_VALUE": "3"}
    app._fetch = lambda dataset, month: [airport_row] if dataset.startswith("airport_") else [territory_row]

    airport, territory = app.build_month(202606)

    assert airport[0]["Passengers"] == 6
    assert territory[0]["Passengers"] == 3
