import csv
from pathlib import Path

from create_dimensions.main import write_dimensions
from model_update.main import update_predictions
from pipeline.pipeline import run_pipeline
from pipeline.transform import transform_traffic_per_airport, transform_traffic_per_territory


def test_fresh_dimensions_pipeline_and_model_flow(tmp_path: Path) -> None:
    data = tmp_path / "data"
    data.mkdir()
    (data / "Final_Territory.csv").write_text("TerritoryId,TerritoryCode,TerritoryName\n1,ES,Tenerife\n", encoding="utf-8")
    (data / "Final_AircraftMovement.csv").write_text("AircraftMovementId,AircraftMovementCode,AircraftMovement\n2,ARR,Arrival\n", encoding="utf-8")
    (data / "AirService.csv").write_text("AirServiceId,AirServiceCode,AirService\n0,PAX,Passengers\n", encoding="utf-8")
    write_dimensions(data, [{"AirportCode": "ES_GCTS", "AirportName": "Tenerife"}], [])
    airports = [{"AirportId": 0, "AirportCode": "ES_GCTS"}]
    services, movements = {"PAX": 0}, {"ARR": 2}
    airport_facts = transform_traffic_per_airport(
        [{"SERVICIO_AEREO_CODE": "PAX", "MOVIMIENTO_AERONAVE_CODE": "ARR", "AEROPUERTO_BASE_CODE": "ES_GCTS", "AEROPUERTO_ESCALA_CODE": "ES_GCTS", "OBS_VALUE": "4"}],
        [], [], airports, services, movements, 202601,
    )
    territory_facts = transform_traffic_per_territory(
        [{"TERRITORIO_CODE": "ES", "AEROPUERTO_ESCALA_CODE": "ES", "SERVICIO_AEREO_CODE": "PAX", "MOVIMIENTO_AERONAVE_CODE": "ARR", "OBS_VALUE": "4"}],
        [], [], {"ES": 1}, services, movements, 202601,
    )
    def build(month):
        return ([{**row, "MonthId": month} for row in airport_facts], [{**row, "MonthId": month} for row in territory_facts])

    run_pipeline(data, "run", build, latest_month="2026-01")
    predictions = update_predictions(data)
    assert predictions[0]["RealPassengers"] == 4
    assert (data / "predictions" / "Predictions.csv").is_file()

    with (data / "TrafficPerAirport.csv").open(newline="") as handle:
        assert list(csv.DictReader(handle))[0]["MonthId"] == "200401"
