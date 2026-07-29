from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping
from typing import Any


class UnresolvedAirportError(ValueError):
    """Raised when facts reference an airport absent from the dimension."""


def _lookup(values: Mapping[str, Any] | Iterable[Mapping[str, Any]], code_column: str, id_column: str) -> dict[str, Any]:
    if isinstance(values, Mapping):
        return dict(values)
    return {str(row[code_column]): row[id_column] for row in values}


def _value(row: Mapping[str, Any]) -> int | float:
    raw = row.get("OBS_VALUE")
    if raw is None or str(raw).strip() == "":
        return 0
    return float(raw) if "." in str(raw) else int(raw)


def _metric(row: Mapping[str, Any], default: str) -> str:
    marker = str(row.get("MEASURE") or row.get("MEDIDAS_CODE") or "").upper()
    return "Mail" if "MAIL" in marker or "CORREO" in marker else default


def transform_traffic_per_airport(
    passenger_rows: Iterable[Mapping[str, Any]], goods_rows: Iterable[Mapping[str, Any]], operation_rows: Iterable[Mapping[str, Any]],
    airports: Mapping[str, Any] | Iterable[Mapping[str, Any]], services: Mapping[str, Any] | Iterable[Mapping[str, Any]], movements: Mapping[str, Any] | Iterable[Mapping[str, Any]], month_id: int,
) -> list[dict[str, Any]]:
    airport_ids = _lookup(airports, "AirportCode", "AirportId")
    service_ids = _lookup(services, "AirServiceCode", "AirServiceId")
    movement_ids = _lookup(movements, "AircraftMovementCode", "AircraftMovementId")
    aggregate: dict[tuple[str, str, str, str], dict[str, Any]] = defaultdict(lambda: {"Passengers": 0, "Goods": 0, "Mail": 0, "Operations": 0})
    unresolved: set[str] = set()

    def consume(rows: Iterable[Mapping[str, Any]], metric: str) -> None:
        for row in rows:
            base = str(row.get("AEROPUERTO_BASE_CODE") or "")
            stopover = str(row.get("AEROPUERTO_ESCALA_CODE") or row.get("AEROPUERTO_ORIGEN_DESTINO_CODE") or "")
            service, movement = str(row.get("SERVICIO_AEREO_CODE") or ""), str(row.get("MOVIMIENTO_AERONAVE_CODE") or "")
            if base not in airport_ids:
                unresolved.add(base)
            if stopover not in airport_ids:
                unresolved.add(stopover)
            key = (base, stopover, service, movement)
            target = _metric(row, metric)
            aggregate[key][target] += _value(row)

    consume(passenger_rows, "Passengers")
    consume(goods_rows, "Goods")
    consume(operation_rows, "Operations")
    if unresolved:
        raise UnresolvedAirportError(f"unresolved airport codes: {sorted(unresolved)}")
    output = []
    for (base, stopover, service, movement), measures in sorted(aggregate.items()):
        if service not in service_ids or movement not in movement_ids:
            raise ValueError(f"missing dimension code: service={service}, movement={movement}")
        output.append({"BaseAirportId": airport_ids[base], "StopoverAirportId": airport_ids[stopover], "AircraftMovementId": movement_ids[movement], "AirServiceId": service_ids[service], "MonthId": month_id, **measures})
    return output


def transform_traffic_per_territory(
    passenger_rows: Iterable[Mapping[str, Any]], goods_rows: Iterable[Mapping[str, Any]], operation_rows: Iterable[Mapping[str, Any]],
    territories: Mapping[str, Any] | Iterable[Mapping[str, Any]], services: Mapping[str, Any] | Iterable[Mapping[str, Any]], movements: Mapping[str, Any] | Iterable[Mapping[str, Any]], month_id: int,
) -> list[dict[str, Any]]:
    territory_ids = _lookup(territories, "TerritoryCode", "TerritoryId")
    service_ids = _lookup(services, "AirServiceCode", "AirServiceId")
    movement_ids = _lookup(movements, "AircraftMovementCode", "AircraftMovementId")
    aggregate: dict[tuple[str, str, str, str], dict[str, Any]] = defaultdict(lambda: {"Passengers": 0, "Goods": 0, "Mail": 0, "Operations": 0})

    def consume(rows: Iterable[Mapping[str, Any]], metric: str) -> None:
        for row in rows:
            key = (str(row.get("TERRITORIO_CODE") or ""), str(row.get("AEROPUERTO_ESCALA_CODE") or row.get("AEROPUERTO_ORIGEN_DESTINO_CODE") or ""), str(row.get("MOVIMIENTO_AERONAVE_CODE") or ""), str(row.get("SERVICIO_AEREO_CODE") or ""))
            target = _metric(row, metric)
            aggregate[key][target] += _value(row)

    consume(passenger_rows, "Passengers")
    consume(goods_rows, "Goods")
    consume(operation_rows, "Operations")
    missing = sorted({code for key in aggregate for code in key[:2] if code not in territory_ids})
    if missing:
        raise ValueError(f"unresolved territory codes: {missing}")
    for key, measures in list(aggregate.items()):
        island, stopover, movement, service = key
        if stopover != "FOREIGN":
            continue
        for excluded in ("DE", "GB"):
            source = aggregate.get((island, excluded, movement, service))
            if source:
                for measure in measures:
                    measures[measure] -= source[measure]
    output = []
    for (territory, stopover, movement, service), measures in sorted(aggregate.items()):
        if service not in service_ids or movement not in movement_ids:
            raise ValueError(f"missing dimension code: service={service}, movement={movement}")
        output.append({"IslandId": territory_ids[territory], "StopoverTerritoryId": territory_ids[stopover], "AircraftMovementId": movement_ids[movement], "AirServiceId": service_ids[service], "MonthId": month_id, **measures})
    return output
