from __future__ import annotations

import csv
import json
import os
import shutil
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Callable


class PipelineError(RuntimeError):
    """Raised when a pipeline run cannot complete atomically."""


def inclusive_months(start: str, end: str) -> list[int]:
    year, month = (int(value) for value in start.split("-"))
    end_year, end_month = (int(value) for value in end.split("-"))
    if (year, month) > (end_year, end_month):
        raise PipelineError("start month must not be after end month")
    result = []
    while (year, month) <= (end_year, end_month):
        result.append(year * 100 + month)
        month += 1
        if month == 13:
            year, month = year + 1, 1
    return result


def _read(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _write(path: Path, rows: list[dict[str, Any]]) -> None:
    columns = sorted({column for row in rows for column in row})
    if "MonthId" in columns:
        columns.remove("MonthId")
        columns.insert(0, "MonthId")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def atomic_replace_facts(data_dir: str | Path, old_airport: list[dict[str, Any]], old_territory: list[dict[str, Any]], new_airport: list[dict[str, Any]], new_territory: list[dict[str, Any]]) -> None:
    data_dir = Path(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    temp_dir = Path(tempfile.mkdtemp(prefix="pipeline-", dir=data_dir))
    destinations = [data_dir / "TrafficPerAirport.csv", data_dir / "TrafficPerTerritory.csv"]
    backups: list[Path | None] = []
    try:
        _write(temp_dir / destinations[0].name, new_airport)
        _write(temp_dir / destinations[1].name, new_territory)
        for destination in destinations:
            backup = temp_dir / f"{destination.name}.bak"
            if destination.exists():
                shutil.copy2(destination, backup)
                backups.append(backup)
            else:
                backups.append(None)
        os.replace(temp_dir / destinations[0].name, destinations[0])
        os.replace(temp_dir / destinations[1].name, destinations[1])
    except OSError as exc:
        for destination, backup in zip(destinations, backups):
            if backup and backup.exists():
                shutil.copy2(backup, destination)
            elif not backup and destination.exists():
                destination.unlink()
        raise PipelineError(f"atomic fact replacement failed: {exc}") from exc
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def _run_metadata(root: Path, data: dict[str, Any]) -> None:
    metadata_dir = root / "runtime" / "run_metadata"
    metadata_dir.mkdir(parents=True, exist_ok=True)
    (metadata_dir / f"{data['run_id']}.json").write_text(json.dumps(data, indent=2), encoding="utf-8")


def run_pipeline(data_dir: str | Path, mode: str, build_month: Callable[[int], tuple[list[dict[str, Any]], list[dict[str, Any]]]], *, latest_month: str, model_update: Callable[[], Any] | None = None, start: str | None = None, end: str | None = None) -> dict[str, Any]:
    data_dir = Path(data_dir)
    root = data_dir.parent
    run_id = uuid.uuid4().hex
    started = datetime.now().astimezone().isoformat()
    metadata: dict[str, Any] = {"run_id": run_id, "mode": mode, "requested_period": start or latest_month, "status": "running", "rows_received": {}, "rows_inserted_or_replaced": {}, "started_at": started}
    try:
        airport_path, territory_path = data_dir / "TrafficPerAirport.csv", data_dir / "TrafficPerTerritory.csv"
        old_airport, old_territory = _read(airport_path), _read(territory_path)
        existing = {int(row["MonthId"]) for row in old_airport if row.get("MonthId", "").isdigit()}
        latest = inclusive_months(latest_month, latest_month)[0]
        if mode == "backfill":
            if not start or not end:
                raise PipelineError("backfill requires --start and --end")
            if not airport_path.exists() or not territory_path.exists():
                raise PipelineError("backfill requires existing fact tables")
            selected = inclusive_months(start, end)
            if existing and any(month not in existing for month in inclusive_months("2004-01", latest_month)):
                raise PipelineError("fact tables contain gaps")
            metadata["requested_period"] = {"start": start, "end": end}
        elif mode == "run":
            if start:
                requested = inclusive_months(start, start)
                if requested[0] in existing:
                    raise PipelineError("month already exists; use backfill")
                if any(month not in existing for month in inclusive_months("2004-01", start)[:-1]):
                    raise PipelineError("earlier months are missing")
                selected = requested
            elif not existing:
                selected = inclusive_months("2004-01", latest_month)
            else:
                selected = [month for month in inclusive_months("2004-01", latest_month) if month not in existing]
                if not selected:
                    metadata.update({"status": "success", "finished_at": datetime.now().astimezone().isoformat()})
                    _run_metadata(root, metadata)
                    return metadata
        else:
            raise PipelineError(f"unknown pipeline mode: {mode}")
        replacements_airport: list[dict[str, Any]] = []
        replacements_territory: list[dict[str, Any]] = []
        for month in selected:
            airport_rows, territory_rows = build_month(month)
            replacements_airport.extend(airport_rows)
            replacements_territory.extend(territory_rows)
        selected_set = set(selected)
        combined_airport = [row for row in old_airport if int(row.get("MonthId", 0)) not in selected_set] + replacements_airport
        combined_territory = [row for row in old_territory if int(row.get("MonthId", 0)) not in selected_set] + replacements_territory
        atomic_replace_facts(data_dir, old_airport, old_territory, combined_airport, combined_territory)
        if model_update:
            model_update()
        metadata.update({"status": "success", "rows_received": {"TrafficPerAirport": len(replacements_airport), "TrafficPerTerritory": len(replacements_territory)}, "rows_inserted_or_replaced": {"TrafficPerAirport": len(replacements_airport), "TrafficPerTerritory": len(replacements_territory)}, "finished_at": datetime.now().astimezone().isoformat()})
    except Exception as exc:
        metadata.update({"status": "failed", "error_type": type(exc).__name__, "error_message": str(exc), "finished_at": datetime.now().astimezone().isoformat()})
        _run_metadata(root, metadata)
        raise
    _run_metadata(root, metadata)
    return metadata
