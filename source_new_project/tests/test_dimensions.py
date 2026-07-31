from pathlib import Path

from create_dimensions.main import build_airport_dimension, generate_calendar, write_dimensions


def test_calendar_boundaries_and_month_ids() -> None:
    months = generate_calendar("2004-01", "2099-12")
    assert len(months) == 1152
    assert months[0]["MonthId"] == 200401
    assert months[0]["MonthStartDate"] == "2004-01-01"
    assert months[-1]["MonthId"] == 209912
    assert months[-1]["YearMonth"] == "2099-12"


def test_airport_filtering_preserves_valid_unmatched_and_nullable_coordinates() -> None:
    airports = [
        {"AirportCode": "ES_GCTS", "AirportName": "Tenerife", "Latitude": "", "Longitude": ""},
        {"AirportCode": "DE_EDDT", "AirportName": "Berlin", "Latitude": "", "Longitude": ""},
        {"AirportCode": "GB_EGCN", "AirportName": "Doncaster", "Latitude": "53", "Longitude": "-1"},
        {"AirportCode": "ES70", "AirportName": "aggregate"},
        {"AirportCode": "GB_O", "AirportName": "aggregate"},
        {"AirportCode": "FOREIGN", "AirportName": "aggregate"},
    ]

    result = build_airport_dimension(airports, [])
    codes = [row["AirportCode"] for row in result]
    assert codes == ["DE_EDDT", "ES_GCTS", "GB_EGCN"]
    assert result[1]["Latitude"] is None
    assert result[0]["IcaoCode"] == "EDDT"


def test_dimension_outputs_are_deterministic(tmp_path: Path) -> None:
    source = [{"AirportCode": "ES_GCTS", "AirportName": "Tenerife"}]
    first = tmp_path / "first"
    second = tmp_path / "second"
    for directory in (first, second):
        (directory / "reference").mkdir(parents=True)
        (directory / "reference" / "Territory.csv").write_text("TerritoryId,TerritoryCode,TerritoryName\n1,ES,Tenerife\n", encoding="utf-8")
        (directory / "reference" / "AircraftMovement.csv").write_text("AircraftMovementId,AircraftMovementCode,AircraftMovement\n1,ARR,Arrival\n", encoding="utf-8")
        (directory / "reference" / "AirService.csv").write_text("AirServiceId,AirServiceCode,AirService\n1,PAX,Passengers\n", encoding="utf-8")
    write_dimensions(first, source, [])
    write_dimensions(second, source, [])
    assert (first / "CalendarMonth.csv").read_bytes() == (second / "CalendarMonth.csv").read_bytes()
    assert (first / "Airport.csv").read_bytes() == (second / "Airport.csv").read_bytes()
    assert {path.name for path in first.glob("*.csv")} == {"Airport.csv", "Territory.csv", "AircraftMovement.csv", "AirService.csv", "CalendarMonth.csv"}


def test_known_enrichment_match_and_dimension_schema() -> None:
    rows = build_airport_dimension(
        [{"AirportCode": "GB_EGPF", "AirportName": "Glasgow"}],
        [{"AirportCode": "GB_EGPF", "latitude_deg": "55.87", "longitude_deg": "-4.43"}],
    )
    assert rows[0]["IcaoCode"] == "EGPF"
    assert rows[0]["Latitude"] == 55.87
    assert list(rows[0]) == ["AirportId", "AirportName", "AirportCode", "IcaoCode", "Latitude", "Longitude", "CountryCode", "CountryName"]
