import pytest

from pipeline.transform import UnresolvedAirportError, transform_traffic_per_airport, transform_traffic_per_territory


def dimensions():
    airports = [{"AirportId": 1, "AirportCode": "ES_GCTS"}, {"AirportId": 2, "AirportCode": "GB_EGPF", "Latitude": None, "Longitude": None}]
    services = {"PAX": 10}
    movements = {"ARR": 20}
    return airports, services, movements


def test_airport_resolution_aggregation_and_null_measure() -> None:
    airports, services, movements = dimensions()
    rows = transform_traffic_per_airport(
        [{"SERVICIO_AEREO_CODE": "PAX", "MOVIMIENTO_AERONAVE_CODE": "ARR", "AEROPUERTO_BASE_CODE": "ES_GCTS", "AEROPUERTO_ESCALA_CODE": "GB_EGPF", "OBS_VALUE": None}],
        [{"SERVICIO_AEREO_CODE": "PAX", "MOVIMIENTO_AERONAVE_CODE": "ARR", "AEROPUERTO_BASE_CODE": "ES_GCTS", "AEROPUERTO_ESCALA_CODE": "GB_EGPF", "OBS_VALUE": "3"}],
        [], airports, services, movements, 202606,
    )
    assert rows == [{"BaseAirportId": 1, "StopoverAirportId": 2, "AircraftMovementId": 20, "AirServiceId": 10, "MonthId": 202606, "Passengers": 0, "Goods": 3, "Mail": 0, "Operations": 0}]


def test_missing_airport_fails_and_coordinates_do_not_matter() -> None:
    airports, services, movements = dimensions()
    source = [{"SERVICIO_AEREO_CODE": "PAX", "MOVIMIENTO_AERONAVE_CODE": "ARR", "AEROPUERTO_BASE_CODE": "ES_GCTS", "AEROPUERTO_ESCALA_CODE": "NO_UNKNOWN", "OBS_VALUE": "1"}]
    with pytest.raises(UnresolvedAirportError, match="NO_UNKNOWN"):
        transform_traffic_per_airport(source, [], [], airports, services, movements, 202606)


def test_territory_foreign_correction_uses_codes_and_deduplicates() -> None:
    territories = {"FOREIGN": 9, "DE": 3, "GB": 4, "ES": 1}
    services = {"PAX": 10}
    movements = {"ARR": 20}
    rows = [
        {"TERRITORIO_CODE": "ES", "AEROPUERTO_ESCALA_CODE": "FOREIGN", "SERVICIO_AEREO_CODE": "PAX", "MOVIMIENTO_AERONAVE_CODE": "ARR", "OBS_VALUE": "10"},
        {"TERRITORIO_CODE": "ES", "AEROPUERTO_ESCALA_CODE": "DE", "SERVICIO_AEREO_CODE": "PAX", "MOVIMIENTO_AERONAVE_CODE": "ARR", "OBS_VALUE": "2"},
        {"TERRITORIO_CODE": "ES", "AEROPUERTO_ESCALA_CODE": "GB", "SERVICIO_AEREO_CODE": "PAX", "MOVIMIENTO_AERONAVE_CODE": "ARR", "OBS_VALUE": "3"},
        {"TERRITORIO_CODE": "ES", "AEROPUERTO_ESCALA_CODE": "ES", "SERVICIO_AEREO_CODE": "PAX", "MOVIMIENTO_AERONAVE_CODE": "ARR", "OBS_VALUE": "4"},
    ]
    output = transform_traffic_per_territory(rows, [], [], territories, services, movements, 202606)
    by_id = {row["StopoverTerritoryId"]: row["Passengers"] for row in output}
    assert by_id == {9: 5, 3: 2, 4: 3, 1: 4}
