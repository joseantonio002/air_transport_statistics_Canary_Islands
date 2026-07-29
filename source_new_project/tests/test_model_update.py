from pathlib import Path

import pytest

from model_update.main import ModelUpdateError, month_id_to_date, update_predictions


def test_month_id_conversion() -> None:
    assert month_id_to_date(202606) == "2026-06-01"
    with pytest.raises(ModelUpdateError):
        month_id_to_date(202613)


def test_prediction_output_schema_and_known_fixture(tmp_path: Path) -> None:
    data = tmp_path / "data"
    data.mkdir()
    (data / "TrafficPerTerritory.csv").write_text(
        "IslandId,AirServiceId,AircraftMovementId,MonthId,Passengers\n1,0,2,202601,10\n1,0,2,202602,12\n", encoding="utf-8"
    )
    (data / "Territory.csv").write_text("TerritoryId,TerritoryCode,TerritoryName\n1,ES,Tenerife\n", encoding="utf-8")

    output = update_predictions(data)

    assert list(output[0]) == ["Island", "Month", "RealPassengers", "yhat_lower", "yhat", "yhat_upper"]
    assert output[0]["Island"] == "Tenerife"
    assert output[0]["RealPassengers"] == 10
    assert output[-1]["Month"] == "2027-02-01"


def test_missing_inputs_fail(tmp_path: Path) -> None:
    (tmp_path / "data").mkdir()
    with pytest.raises(ModelUpdateError, match="TrafficPerTerritory"):
        update_predictions(tmp_path / "data")
