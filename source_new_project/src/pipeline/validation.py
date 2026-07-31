from __future__ import annotations

import csv
import logging
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


class ContractValidationError(ValueError):
    """Raised when a dataset violates its declared contract."""


@dataclass(frozen=True)
class ValidationResult:
    dataset: str
    row_count: int


def _fail(dataset: str, contract: Path, message: str, rows: list[dict[str, str]] | None = None) -> None:
    sample = f"; sample={rows[:20]}" if rows else ""
    error = ContractValidationError(f"dataset '{dataset}' ({contract}): {message}{sample}")
    logger.error(str(error))
    raise error


def _is_null(value: str | None) -> bool:
    return value is None or value.strip() == ""


def _valid_value(value: str, type_name: str) -> bool:
    if type_name in {"string", "str"}:
        return True
    if type_name in {"integer", "bigint", "int"}:
        try:
            int(value)
            return True
        except ValueError:
            return False
    if type_name in {"number", "float", "double"}:
        try:
            float(value)
            return True
        except ValueError:
            return False
    if type_name == "date":
        try:
            date.fromisoformat(value)
            return True
        except ValueError:
            return False
    return True


def _month_valid(value: str) -> bool:
    if len(value) != 6 or not value.isdigit():
        return False
    return 1 <= int(value[4:]) <= 12


def _contract_document(contract_path: Path) -> dict[str, Any]:
    try:
        document = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ContractValidationError(f"cannot read contract {contract_path}: {exc}") from exc
    if not isinstance(document, dict) or not document.get("dataset") or not isinstance(document.get("schema"), dict):
        raise ContractValidationError(f"invalid contract structure: {contract_path}")
    return document


def validate_csv(
    data_path: str | Path,
    contract_path: str | Path,
    reference_tables: dict[str, str | Path] | None = None,
) -> ValidationResult:
    data_path = Path(data_path)
    contract_path = Path(contract_path)
    document = _contract_document(contract_path)
    dataset = str(document["dataset"])
    schema = {key: value for key, value in document["schema"].items() if key != "relationships"}
    try:
        with data_path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            columns = reader.fieldnames or []
            rows = list(reader)
    except OSError as exc:
        _fail(dataset, contract_path, f"cannot read data file {data_path}: {exc}")
    missing = [column for column in schema if column not in columns]
    if missing:
        _fail(dataset, contract_path, f"missing required columns: {missing}")
    for column, definition in schema.items():
        type_name = str(definition.get("type", "string"))
        nullable = bool(definition.get("nullable", True))
        null_rows = [row for row in rows if _is_null(row.get(column))]
        if null_rows and not nullable:
            _fail(dataset, contract_path, f"nullability violation in column '{column}'", null_rows)
        bad_rows = [row for row in rows if not _is_null(row.get(column)) and not _valid_value(str(row[column]), type_name)]
        if bad_rows:
            _fail(dataset, contract_path, f"data type violation in column '{column}'", bad_rows)
        if column == "MonthId":
            bad_months = [row for row in rows if not _is_null(row.get(column)) and not _month_valid(str(row[column]))]
            if bad_months:
                _fail(dataset, contract_path, "invalid month in column 'MonthId'", bad_months)
        if "TIME_PERIOD" in column and column.endswith("CODE"):
            bad_dates = [row for row in rows if not _is_null(row.get(column)) and not _valid_month_text(str(row[column]))]
            if bad_dates:
                _fail(dataset, contract_path, f"invalid date/month in column '{column}'", bad_dates)
    quality = document.get("quality") or {}
    natural_key = quality.get("natural_key", [])
    if natural_key:
        seen: set[tuple[str, ...]] = set()
        duplicates = []
        for row in rows:
            key = tuple(row.get(column, "") for column in natural_key)
            if key in seen:
                duplicates.append(row)
            seen.add(key)
        if duplicates:
            _fail(dataset, contract_path, f"duplicate natural key {natural_key}", duplicates)
    volume = document.get("volume") or {}
    rule = next(iter(volume.values()), None)
    if isinstance(rule, dict):
        minimum, maximum = rule.get("minimum_rows"), rule.get("maximum_rows")
        if minimum is not None and len(rows) < minimum or maximum is not None and len(rows) > maximum:
            _fail(dataset, contract_path, f"row count {len(rows)} outside expected range {minimum}..{maximum}")
    relationships = document["schema"].get("relationships", [])
    for relationship in relationships:
        if not reference_tables:
            _fail(dataset, contract_path, "foreign-key references were not supplied")
        from_column = relationship["from"]
        target_dataset, target_column = str(relationship["to"]).split(".", 1)
        reference_path = reference_tables.get(target_dataset)
        if reference_path is None:
            _fail(dataset, contract_path, f"missing foreign-key reference dataset '{target_dataset}'")
        with Path(reference_path).open(newline="", encoding="utf-8") as handle:
            reference_rows = {row.get(target_column, "") for row in csv.DictReader(handle)}
        bad_rows = [row for row in rows if row.get(from_column, "") not in reference_rows]
        if bad_rows:
            _fail(dataset, contract_path, f"foreign-key violation for '{from_column}' -> '{relationship['to']}'", bad_rows)
    return ValidationResult(dataset, len(rows))


def _valid_month_text(value: str) -> bool:
    if len(value) == 7 and value[4] == "-":
        try:
            date.fromisoformat(f"{value}-01")
            return True
        except ValueError:
            return False
    return _valid_date_text(value)


def _valid_date_text(value: str) -> bool:
    try:
        date.fromisoformat(value)
        return True
    except ValueError:
        return False


def validate_contract_datasets(data_root: str | Path, contract_root: str | Path) -> list[ValidationResult]:
    data_root, contract_root = Path(data_root), Path(contract_root)
    results = []
    for contract_path in sorted(contract_root.glob("*.yaml")):
        document = _contract_document(contract_path)
        source_path = document.get("source", {}).get("path")
        if not source_path:
            continue
        data_path = data_root / Path(source_path).name
        if not data_path.is_file():
            _fail(str(document["dataset"]), contract_path, f"missing source dataset: {data_path}")
        results.append(validate_csv(data_path, contract_path))
    return results


def validate_records(
    records: list[dict[str, Any]],
    contract_path: str | Path,
    reference_tables: dict[str, str | Path] | None = None,
) -> ValidationResult:
    """Validate extracted records without writing the raw API response to disk."""
    contract_path = Path(contract_path)
    document = _contract_document(contract_path)
    dataset = str(document["dataset"])
    schema = {key: value for key, value in document["schema"].items() if key != "relationships"}
    columns = set().union(*(row.keys() for row in records)) if records else set()
    missing = [column for column in schema if column not in columns]
    if missing:
        _fail(dataset, contract_path, f"missing required columns: {missing}")
    for column, definition in schema.items():
        type_name = str(definition.get("type", "string"))
        nullable = bool(definition.get("nullable", True))
        null_rows = [row for row in records if _is_null(row.get(column))]
        if null_rows and not nullable:
            _fail(dataset, contract_path, f"nullability violation in column '{column}'", null_rows)
        bad_rows = [row for row in records if not _is_null(row.get(column)) and not _valid_value(str(row[column]), type_name)]
        if bad_rows:
            _fail(dataset, contract_path, f"data type violation in column '{column}'", bad_rows)
        if column == "MonthId":
            bad_months = [row for row in records if not _is_null(row.get(column)) and not _month_valid(str(row[column]))]
            if bad_months:
                _fail(dataset, contract_path, "invalid month in column 'MonthId'", bad_months)
    quality = document.get("quality") or {}
    natural_key = quality.get("natural_key", [])
    if natural_key:
        seen: set[tuple[str, ...]] = set()
        duplicates = []
        for row in records:
            key = tuple(str(row.get(column, "")) for column in natural_key)
            if key in seen:
                duplicates.append(row)
            seen.add(key)
        if duplicates:
            _fail(dataset, contract_path, f"duplicate natural key {natural_key}", duplicates)
    volume = document.get("volume") or {}
    rule = next(iter(volume.values()), None)
    if isinstance(rule, dict):
        minimum, maximum = rule.get("minimum_rows"), rule.get("maximum_rows")
        if minimum is not None and len(records) < minimum or maximum is not None and len(records) > maximum:
            _fail(dataset, contract_path, f"row count {len(records)} outside expected range {minimum}..{maximum}")
    return ValidationResult(dataset, len(records))
