from pathlib import Path

import pytest
import yaml

from pipeline.validation import ContractValidationError, validate_csv, validate_contract_datasets


def make_contract(root: Path, schema: dict, **extra: object) -> Path:
    path = root / "contract.yaml"
    document = {"dataset": "facts", "schema": schema, **extra}
    path.write_text(yaml.safe_dump(document), encoding="utf-8")
    return path


def write_csv(root: Path, name: str, content: str) -> Path:
    path = root / name
    path.write_text(content, encoding="utf-8")
    return path


def test_validates_types_nullability_and_extra_columns(tmp_path: Path) -> None:
    contract = make_contract(
        tmp_path,
        {"MonthId": {"type": "integer", "nullable": False}, "Value": {"type": "number", "nullable": True}},
    )
    data = write_csv(tmp_path, "facts.csv", "MonthId,Value,Extra\n202606,1.5,ok\n")

    assert validate_csv(data, contract).row_count == 1


@pytest.mark.parametrize(
    ("content", "message"),
    [("Value\n1\n", "missing required columns"), ("MonthId,Value\n,1\n", "nullability"), ("MonthId,Value\nabc,1\n", "data type")],
)
def test_rejects_bad_schema_rows(tmp_path: Path, content: str, message: str) -> None:
    contract = make_contract(tmp_path, {"MonthId": {"type": "integer", "nullable": False}, "Value": {"type": "number", "nullable": False}})
    data = write_csv(tmp_path, "facts.csv", content)

    with pytest.raises(ContractValidationError, match=message):
        validate_csv(data, contract)


def test_rejects_duplicate_natural_keys_and_wrong_volume(tmp_path: Path) -> None:
    contract = make_contract(
        tmp_path,
        {"MonthId": {"type": "integer", "nullable": False}, "Value": {"type": "integer", "nullable": False}},
        quality={"natural_key": ["MonthId"], "duplicates": {"maximum": 0}},
        volume={"monthly": {"minimum_rows": 3, "maximum_rows": 3}},
    )
    data = write_csv(tmp_path, "facts.csv", "MonthId,Value\n202606,1\n202606,2\n")

    with pytest.raises(ContractValidationError, match="natural key") as error:
        validate_csv(data, contract)
    assert "facts" in str(error.value)
    assert str(contract) in str(error.value)


def test_rejects_invalid_month_and_foreign_keys(tmp_path: Path) -> None:
    contract = make_contract(tmp_path, {"MonthId": {"type": "integer", "nullable": False}, "AirportId": {"type": "integer", "nullable": False}, "relationships": [{"from": "AirportId", "to": "airport.AirportId"}]})
    # Keep both failures independently observable and capped in the exception.
    data = write_csv(tmp_path, "facts.csv", "MonthId,AirportId\n202613,99\n")
    airport = write_csv(tmp_path, "Airport.csv", "AirportId\n1\n")

    with pytest.raises(ContractValidationError, match="month"):
        validate_csv(data, contract, reference_tables={"airport": airport})

    valid_data = write_csv(tmp_path, "valid-month.csv", "MonthId,AirportId\n202606,99\n")
    with pytest.raises(ContractValidationError, match="foreign-key"):
        validate_csv(valid_data, contract, reference_tables={"airport": airport})


def test_missing_dataset_is_reported(tmp_path: Path) -> None:
    contract_dir = tmp_path / "contracts"
    contract_dir.mkdir()
    contract = contract_dir / "facts.yaml"
    contract.write_text(yaml.safe_dump({"dataset": "facts", "source": {"path": "data/facts.csv"}, "schema": {"Id": {"type": "integer", "nullable": False}}}), encoding="utf-8")

    with pytest.raises(ContractValidationError, match="missing source dataset"):
        validate_contract_datasets(tmp_path / "data", contract_dir)
