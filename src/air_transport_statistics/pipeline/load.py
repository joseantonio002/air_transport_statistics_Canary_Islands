from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path

import duckdb

from .common import PipelineError, TransformResult, month_id, month_range, relation_for_csv, sql_path, validate_relation

LOGGER = logging.getLogger(__name__)


def _dimension_path(data_dir: Path, preferred: str, fallback: str | None = None) -> Path:
    path = data_dir / preferred
    if path.is_file():
        return path
    if fallback:
        fallback_path = data_dir / fallback
        if fallback_path.is_file():
            return fallback_path
    raise PipelineError(f"missing dimension table: {path}")


def _create_dimension_views(con: duckdb.DuckDBPyConnection, data_dir: Path) -> None:
    values = {
        "airport": _dimension_path(data_dir, "Airport.csv"),
        "territory": _dimension_path(data_dir, "Territory.csv"),
        "airservice": _dimension_path(data_dir, "AirService.csv"),
        "aircraftmovement": _dimension_path(data_dir, "AircraftMovement.csv", "Final_AircraftMovement.csv"),
        "calendarmonth": _dimension_path(data_dir, "CalendarMonth.csv"),
    }
    for name, path in values.items():
        con.execute(f"CREATE OR REPLACE VIEW {name} AS SELECT * FROM {relation_for_csv(path)}")


def _validate_tables(con: duckdb.DuckDBPyConnection, config: object, expected_periods: int) -> dict[str, int]:
    _create_dimension_views(con, config.paths.data)
    contract_dir = config.paths.contracts / "output_data_contracts"
    airport_rows = validate_relation(
        con,
        "traffic_per_airport",
        contract_dir / "traffic_per_airport.yaml",
        period_column="MonthId",
        expected_periods=expected_periods,
        dimensions={
            "BaseAirportId": ("airport", "AirportId"),
            "StopoverAirportId": ("airport", "AirportId"),
            "AircraftMovementId": ("aircraftmovement", "AircraftMovementId"),
            "AirServiceId": ("airservice", "AirServiceId"),
            "MonthId": ("calendarmonth", "MonthId"),
        },
    )
    territory_rows = validate_relation(
        con,
        "traffic_per_territory",
        contract_dir / "traffic_per_territory.yaml",
        period_column="MonthId",
        expected_periods=expected_periods,
        dimensions={
            "IslandId": ("territory", "TerritoryId"),
            "StopoverTerritoryId": ("territory", "TerritoryId"),
            "AircraftMovementId": ("aircraftmovement", "AircraftMovementId"),
            "AirServiceId": ("airservice", "AirServiceId"),
            "MonthId": ("calendarmonth", "MonthId"),
        },
    )
    return {"TrafficPerAirport": airport_rows, "TrafficPerTerritory": territory_rows}


def _copy_table(con: duckdb.DuckDBPyConnection, table: str, path: Path) -> None:
    con.execute(
        f"COPY (SELECT * FROM {table} ORDER BY MonthId) TO {sql_path(path)} "
        "(HEADER, DELIMITER ',', QUOTE '\"', ESCAPE '\"')"
    )


def validate_existing(config: object, airport_path: Path, territory_path: Path) -> int:
    with duckdb.connect() as con:
        _create_dimension_views(con, config.paths.data)
        con.execute(f"CREATE VIEW traffic_per_airport AS SELECT * FROM {relation_for_csv(airport_path)}")
        con.execute(f"CREATE VIEW traffic_per_territory AS SELECT * FROM {relation_for_csv(territory_path)}")
        first_month, last_month = con.execute(
            "SELECT MIN(MonthId), MAX(MonthId) FROM traffic_per_airport"
        ).fetchone()
        if first_month is None or last_month is None:
            raise PipelineError("existing fact tables are empty")
        expected_periods = len(month_range(first_month, last_month))
        _validate_tables(con, config, expected_periods)
        territory_first, territory_last = con.execute(
            "SELECT MIN(MonthId), MAX(MonthId) FROM traffic_per_territory"
        ).fetchone()
        if (first_month, last_month) != (territory_first, territory_last):
            raise PipelineError("fact tables do not cover the same period")
        return last_month


def load(config: object, transform_result: TransformResult, start_month: str, end_month: str) -> dict[str, int]:
    database_path = transform_result.database_path
    data_dir = config.paths.data
    previous_dir = config.paths.previous_version
    temporary_dir = config.paths.temporary
    temporary_dir.mkdir(parents=True, exist_ok=True)
    previous_dir.mkdir(parents=True, exist_ok=True)
    table_names = {
        "TrafficPerAirport": "traffic_per_airport",
        "TrafficPerTerritory": "traffic_per_territory",
    }
    output_paths = {
        "TrafficPerAirport": data_dir / "TrafficPerAirport.csv",
        "TrafficPerTerritory": data_dir / "TrafficPerTerritory.csv",
    }
    staged_paths = {
      name: output_path.with_name(f".{output_path.name}.staged")
      for name, output_path in output_paths.items()
    }
    with duckdb.connect(str(database_path)) as con:
        first_month, last_month = con.execute(
            "SELECT MIN(MonthId), MAX(MonthId) FROM traffic_per_airport"
        ).fetchone()
        expected_periods = len(month_range(first_month, last_month))
        rows = _validate_tables(con, config, expected_periods)
        for name, staged_path in staged_paths.items():
            staged_path.unlink(missing_ok=True)
            _copy_table(con, table_names[name], staged_path)
        for name, staged_path in staged_paths.items():
            with duckdb.connect() as validation_con:
                _create_dimension_views(validation_con, data_dir)
                relation = relation_for_csv(staged_path)
                validation_con.execute(f"CREATE VIEW staged AS SELECT * FROM {relation}")
                contract = config.paths.contracts / "output_data_contracts" / (
                    "traffic_per_airport.yaml" if name == "TrafficPerAirport" else "traffic_per_territory.yaml"
                )
                validate_relation(
                    validation_con,
                    "staged",
                    contract,
                    period_column="MonthId",
                    expected_periods=expected_periods,
                    dimensions=(
                        {
                            "BaseAirportId": ("airport", "AirportId"),
                            "StopoverAirportId": ("airport", "AirportId"),
                            "AircraftMovementId": ("aircraftmovement", "AircraftMovementId"),
                            "AirServiceId": ("airservice", "AirServiceId"),
                            "MonthId": ("calendarmonth", "MonthId"),
                        }
                        if name == "TrafficPerAirport"
                        else {
                            "IslandId": ("territory", "TerritoryId"),
                            "StopoverTerritoryId": ("territory", "TerritoryId"),
                            "AircraftMovementId": ("aircraftmovement", "AircraftMovementId"),
                            "AirServiceId": ("airservice", "AirServiceId"),
                            "MonthId": ("calendarmonth", "MonthId"),
                        }
                    ),
                )
    for name, output_path in output_paths.items():
        if output_path.is_file():
            shutil.copy2(output_path, previous_dir / output_path.name)
    for name, output_path in output_paths.items():
        os.replace(staged_paths[name], output_path)
    return transform_result.rows_inserted_or_replaced
