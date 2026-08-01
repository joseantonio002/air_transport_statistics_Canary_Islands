from __future__ import annotations

import logging
from pathlib import Path

import duckdb

from .common import (
    ExtractionResult,
    PipelineError,
    TransformResult,
    month_id,
    month_range,
    relation_for_csv,
    sql_path,
    validate_relation,
)

LOGGER = logging.getLogger(__name__)

AIRPORT_KEYS = "service, movement, month, base, stopover"
TERRITORY_KEYS = "territory, stopover, movement, service, month"


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
    dimensions = {
        "airport": _dimension_path(data_dir, "Airport.csv"),
        "territory": _dimension_path(data_dir, "Territory.csv"),
        "airservice": _dimension_path(data_dir, "AirService.csv"),
        "aircraftmovement": _dimension_path(data_dir, "AircraftMovement.csv", "AircraftMovement.csv"),
        "calendarmonth": _dimension_path(data_dir, "CalendarMonth.csv"),
    }
    for name, path in dimensions.items():
        con.execute(
            f"CREATE OR REPLACE VIEW {name} AS SELECT * FROM {relation_for_csv(path)}"
        )


def _airport_source(path: Path, operation: bool = False) -> str:
    stopover = "AEROPUERTO_ORIGEN_DESTINO_CODE" if operation else "AEROPUERTO_ESCALA_CODE"
    return (
        f"SELECT SERVICIO_AEREO_CODE AS service, MOVIMIENTO_AERONAVE_CODE AS movement, "
        f"TIME_PERIOD_CODE AS month, AEROPUERTO_BASE_CODE AS base, "
        f"{stopover} AS stopover, MEDIDAS_CODE AS measure, "
        f"TRY_CAST(NULLIF(OBS_VALUE, '') AS DOUBLE) AS value "
        f"FROM {relation_for_csv(path, all_varchar=True)}"
    )


def _territory_source(path: Path, operation: bool = False) -> str:
    stopover = "AEROPUERTO_ORIGEN_DESTINO_CODE" if operation else "AEROPUERTO_ESCALA_CODE"
    return (
        f"SELECT TERRITORIO_CODE AS territory, {stopover} AS stopover, "
        f"MOVIMIENTO_AERONAVE_CODE AS movement, SERVICIO_AEREO_CODE AS service, "
        f"TIME_PERIOD_CODE AS month, MEDIDAS_CODE AS measure, "
        f"TRY_CAST(NULLIF(OBS_VALUE, '') AS DOUBLE) AS value "
        f"FROM {relation_for_csv(path, all_varchar=True)}"
    )


def _measure_union(files: dict[str, object], names: list[str], operation: bool = False, measure: str | None = None) -> str:
    parts = []
    for name in names:
        source = _airport_source(files[name].path, operation=operation)
        if measure:
            source += f" WHERE measure = '{measure}'"
        parts.append(source)
    return " UNION ALL ".join(parts)


def _airport_table(con: duckdb.DuckDBPyConnection, extracted: ExtractionResult, existing: Path | None, data_dir: Path) -> int:
    files = extracted.files
    passengers = _measure_union(files, ["total_passengers", "arrival_passengers", "departure_passengers"])
    operations = _measure_union(files, ["total_operations", "arrival_operations", "departure_operations"], operation=True)
    goods = _measure_union(files, ["total_goods_mails", "arrival_goods_mails", "departure_goods_mails"], measure="MERCANCIA", operation=False)
    mail = _measure_union(files, ["total_goods_mails", "arrival_goods_mails", "departure_goods_mails"], measure="CORREO", operation=False)
    keys = "service, movement, month, base, stopover"
    con.execute(f"CREATE OR REPLACE TEMP VIEW airport_passengers AS {passengers}")
    con.execute(f"CREATE OR REPLACE TEMP VIEW airport_operations AS {operations}")
    con.execute(f"CREATE OR REPLACE TEMP VIEW airport_goods AS {goods}")
    con.execute(f"CREATE OR REPLACE TEMP VIEW airport_mail AS {mail}")
    combined = f"""
        SELECT
            COALESCE(p.service, o.service, g.service, m.service) AS service,
            COALESCE(p.movement, o.movement, g.movement, m.movement) AS movement,
            COALESCE(p.month, o.month, g.month, m.month) AS month,
            COALESCE(p.base, o.base, g.base, m.base) AS base,
            COALESCE(p.stopover, o.stopover, g.stopover, m.stopover) AS stopover,
            COALESCE(p.value, 0)::BIGINT AS passengers,
            COALESCE(o.value, 0)::BIGINT AS operations,
            COALESCE(g.value, 0)::BIGINT AS goods,
            COALESCE(m.value, 0)::BIGINT AS mail
        FROM airport_passengers p
        FULL OUTER JOIN airport_operations o USING ({keys})
        FULL OUTER JOIN airport_goods g USING ({keys})
        FULL OUTER JOIN airport_mail m USING ({keys})
    """
    mapped = f"""
        SELECT
            base_airport.AirportId::INTEGER AS BaseAirportId,
            stop_airport.AirportId::INTEGER AS StopoverAirportId,
            am.AircraftMovementId::INTEGER AS AircraftMovementId,
            s.AirServiceId::INTEGER AS AirServiceId,
            CAST(REPLACE(c.month, '-M', '') AS INTEGER) AS MonthId,
            c.passengers::BIGINT AS Passengers,
            c.goods::BIGINT AS Goods,
            c.mail::BIGINT AS Mail,
            c.operations::BIGINT AS Operations
        FROM ({combined}) c
        JOIN airport base_airport ON c.base = base_airport.AirportCode
        JOIN airport stop_airport ON c.stopover = stop_airport.AirportCode
        JOIN airservice s ON c.service = s.AirServiceCode
        JOIN aircraftmovement am ON c.movement = am.AircraftMovementCode
    """
    con.execute(f"CREATE OR REPLACE TABLE new_traffic_per_airport AS {mapped}")
    if existing:
        con.execute(
            f"CREATE OR REPLACE TABLE traffic_per_airport AS "
            f"SELECT * FROM {relation_for_csv(existing)} WHERE MonthId < {month_id(extracted.start_month)} "
            f"UNION ALL SELECT * FROM new_traffic_per_airport"
        )
    else:
        con.execute("CREATE OR REPLACE TABLE traffic_per_airport AS SELECT * FROM new_traffic_per_airport")
    return con.execute("SELECT COUNT(*) FROM new_traffic_per_airport").fetchone()[0]


def _territory_table(con: duckdb.DuckDBPyConnection, extracted: ExtractionResult, existing: Path | None, data_dir: Path) -> int:
    files = extracted.files
    passengers = _territory_source(files["territory_passengers"].path)
    operations = _territory_source(files["territory_operations"].path, operation=True)
    goods = _territory_source(files["territory_goods_mails"].path) + " WHERE measure = 'MERCANCIA'"
    mail = _territory_source(files["territory_goods_mails"].path) + " WHERE measure = 'CORREO'"
    con.execute(f"CREATE OR REPLACE TEMP VIEW territory_passengers AS {passengers}")
    con.execute(f"CREATE OR REPLACE TEMP VIEW territory_operations AS {operations}")
    con.execute(f"CREATE OR REPLACE TEMP VIEW territory_goods AS {goods}")
    con.execute(f"CREATE OR REPLACE TEMP VIEW territory_mail AS {mail}")
    keys = "territory, stopover, movement, service, month"
    combined = f"""
        SELECT
            COALESCE(p.territory, o.territory, g.territory, m.territory) AS territory,
            COALESCE(p.stopover, o.stopover, g.stopover, m.stopover) AS stopover,
            COALESCE(p.movement, o.movement, g.movement, m.movement) AS movement,
            COALESCE(p.service, o.service, g.service, m.service) AS service,
            COALESCE(p.month, o.month, g.month, m.month) AS month,
            COALESCE(p.value, 0)::BIGINT AS passengers,
            COALESCE(o.value, 0)::BIGINT AS operations,
            COALESCE(g.value, 0)::BIGINT AS goods,
            COALESCE(m.value, 0)::BIGINT AS mail
        FROM territory_passengers p
        FULL OUTER JOIN territory_operations o USING ({keys})
        FULL OUTER JOIN territory_goods g USING ({keys})
        FULL OUTER JOIN territory_mail m USING ({keys})
    """
    mapped = f"""
        SELECT
            t.TerritoryId::INTEGER AS IslandId,
            stop.TerritoryId::INTEGER AS StopoverTerritoryId,
            am.AircraftMovementId::INTEGER AS AircraftMovementId,
            s.AirServiceId::INTEGER AS AirServiceId,
            CAST(REPLACE(c.month, '-M', '') AS INTEGER) AS MonthId,
            c.passengers::BIGINT AS Passengers,
            c.goods::BIGINT AS Goods,
            c.mail::BIGINT AS Mail,
            c.operations::BIGINT AS Operations
        FROM ({combined}) c
        JOIN territory t ON c.territory = t.TerritoryCode
        JOIN territory stop ON c.stopover = stop.TerritoryCode
        JOIN airservice s ON c.service = s.AirServiceCode
        JOIN aircraftmovement am ON c.movement = am.AircraftMovementCode
    """
    con.execute(f"CREATE OR REPLACE TABLE mapped_territory AS {mapped}")
    foreign_id, germany_id, uk_id = con.execute(
        "SELECT "
        "(SELECT TerritoryId FROM territory WHERE TerritoryCode = 'FOREIGN'), "
        "(SELECT TerritoryId FROM territory WHERE TerritoryCode = 'DE'), "
        "(SELECT TerritoryId FROM territory WHERE TerritoryCode = 'GB')"
    ).fetchone()
    if None in (foreign_id, germany_id, uk_id):
        raise PipelineError("Territory dimension is missing FOREIGN, DE, or GB")
    de_keys = (
        "f.IslandId = de.IslandId AND f.AircraftMovementId = de.AircraftMovementId "
        "AND f.AirServiceId = de.AirServiceId AND f.MonthId = de.MonthId"
    )
    gb_keys = (
        "f.IslandId = gb.IslandId AND f.AircraftMovementId = gb.AircraftMovementId "
        "AND f.AirServiceId = gb.AirServiceId AND f.MonthId = gb.MonthId"
    )
    con.execute(f"""
        CREATE OR REPLACE TABLE new_traffic_per_territory AS
        SELECT
            f.IslandId, f.StopoverTerritoryId, f.AircraftMovementId, f.AirServiceId, f.MonthId,
            CASE WHEN f.StopoverTerritoryId = {foreign_id}
                 THEN f.Passengers - COALESCE(de.Passengers, 0) - COALESCE(gb.Passengers, 0)
                 ELSE f.Passengers END AS Passengers,
            CASE WHEN f.StopoverTerritoryId = {foreign_id}
                 THEN f.Goods - COALESCE(de.Goods, 0) - COALESCE(gb.Goods, 0)
                 ELSE f.Goods END AS Goods,
            CASE WHEN f.StopoverTerritoryId = {foreign_id}
                 THEN f.Mail - COALESCE(de.Mail, 0) - COALESCE(gb.Mail, 0)
                 ELSE f.Mail END AS Mail,
            CASE WHEN f.StopoverTerritoryId = {foreign_id}
                 THEN f.Operations - COALESCE(de.Operations, 0) - COALESCE(gb.Operations, 0)
                 ELSE f.Operations END AS Operations
        FROM mapped_territory f
        LEFT JOIN mapped_territory de ON {de_keys} AND de.StopoverTerritoryId = {germany_id}
        LEFT JOIN mapped_territory gb ON {gb_keys} AND gb.StopoverTerritoryId = {uk_id}
    """)
    if existing:
        con.execute(
            f"CREATE OR REPLACE TABLE traffic_per_territory AS "
            f"SELECT * FROM {relation_for_csv(existing)} WHERE MonthId < {month_id(extracted.start_month)} "
            f"UNION ALL SELECT * FROM new_traffic_per_territory"
        )
    else:
        con.execute("CREATE OR REPLACE TABLE traffic_per_territory AS SELECT * FROM new_traffic_per_territory")
    return con.execute("SELECT COUNT(*) FROM new_traffic_per_territory").fetchone()[0]


def transform(
    config: object,
    extracted: ExtractionResult,
    database_path: Path,
    existing_airport: Path | None,
    existing_territory: Path | None,
) -> TransformResult:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(database_path))
    try:
        con.execute(f"SET temp_directory={sql_path(database_path.parent)}")
        _create_dimension_views(con, config.paths.data)
        airport_rows = _airport_table(con, extracted, existing_airport, config.paths.data)
        territory_rows = _territory_table(con, extracted, existing_territory, config.paths.data)
        return TransformResult(database_path, {
            "TrafficPerAirport": airport_rows,
            "TrafficPerTerritory": territory_rows,
        })
    finally:
        con.close()
