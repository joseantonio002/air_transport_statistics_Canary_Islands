from pathlib import Path

import pytest
import yaml


ROOT = Path(__file__).parents[1]
OUTPUT = ROOT / "data_contracts" / "output_data_contracts"
INGESTION = ROOT / "data_contracts" / "ingestion_data_contracts"


def contract(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def test_all_contracts_are_valid_yaml_and_have_required_sections() -> None:
    paths = sorted(ROOT.glob("data_contracts/**/*.yaml"))
    assert paths
    for path in paths:
        document = contract(path)
        assert document["dataset"]
        assert document["schema"]
        assert document["source"]


def test_output_paths_use_canonical_filenames() -> None:
    expected = {
        "airport": "Airport.csv",
        "territory": "Territory.csv",
        "aircraft_movement": "AircraftMovement.csv",
        "air_service": "AirService.csv",
        "calendar_month": "CalendarMonth.csv",
        "traffic_per_airport": "TrafficPerAirport.csv",
        "traffic_per_territory": "TrafficPerTerritory.csv",
    }
    for dataset, filename in expected.items():
        document = contract(next(OUTPUT.glob(f"{dataset}.yaml")))
        assert Path(document["source"]["path"]).name == filename


def test_output_schemas_capture_nullability_keys_and_relationships() -> None:
    airport = contract(OUTPUT / "airport.yaml")
    assert airport["schema"]["AirportCode"]["nullable"] is False
    assert airport["schema"]["IcaoCode"]["nullable"] is True
    assert airport["schema"]["Latitude"]["nullable"] is True
    assert airport["schema"]["Longitude"]["nullable"] is True

    territory = contract(OUTPUT / "territory.yaml")
    assert list(territory["schema"]) == ["TerritoryId", "TerritoryCode", "TerritoryName"]

    for name, key in {
        "traffic_per_airport": ["AirServiceId", "AircraftMovementId", "MonthId", "BaseAirportId", "StopoverAirportId"],
        "traffic_per_territory": ["IslandId", "StopoverTerritoryId", "AircraftMovementId", "AirServiceId", "MonthId"],
    }.items():
        document = contract(OUTPUT / f"{name}.yaml")
        assert document["quality"]["natural_key"] == key
        assert document["schema"]["relationships"]


def test_investigated_monthly_volumes_are_exact() -> None:
    expected = {
        "traffic_per_airport": 17164,
        "traffic_per_territory": 480,
    }
    for name, rows in expected.items():
        volume = contract(OUTPUT / f"{name}.yaml")["volume"]["monthly"]
        assert volume["minimum_rows"] == rows
        assert volume["maximum_rows"] == rows


@pytest.mark.parametrize("dataset_id", ["C00017A_000013", "C00017A_000014", "C00017A_000015"])
def test_territory_ingestion_contracts_exist(dataset_id: str) -> None:
    matches = list(INGESTION.glob(f"{dataset_id}.yaml"))
    assert len(matches) == 1
    document = contract(matches[0])
    assert dataset_id in document["source"]["endpoint"]
