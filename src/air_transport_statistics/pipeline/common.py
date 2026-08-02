from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import duckdb
import yaml


class PipelineError(RuntimeError):
    pass


class AlreadyUpToDateError(PipelineError):
    pass


@dataclass(frozen=True)
class ExtractedFile:
    name: str
    dataset_id: str
    path: Path
    rows: int


@dataclass(frozen=True)
class ExtractionResult:
    files: dict[str, ExtractedFile]
    start_month: str
    end_month: str
    latest_month: str
    rows_received: dict[str, int]


@dataclass(frozen=True)
class TransformResult:
    database_path: Path
    rows_inserted_or_replaced: dict[str, int]


def sql_path(path: Path) -> str:
    return "'" + str(path).replace("'", "''") + "'"


def read_contract(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or not isinstance(value.get("schema"), dict):
        raise PipelineError(f"invalid data contract: {path}")
    return value


def contract_columns(contract: dict[str, Any]) -> list[str]:
    return [name for name, definition in contract["schema"].items() if isinstance(definition, dict)]


def relation_for_csv(path: Path, all_varchar: bool = False) -> str:
    options = "header=true, sample_size=100000, union_by_name=true"
    if all_varchar:
        options += ", all_varchar=true"
    return f"read_csv_auto({sql_path(path)}, {options})"


def _duck_type_matches(actual: str, expected: str) -> bool:
    actual = actual.upper()
    expected = expected.lower()
    if expected == "string":
        return "CHAR" in actual or "VARCHAR" in actual or "TEXT" in actual
    if expected == "integer":
        return actual in {"INTEGER", "BIGINT", "SMALLINT", "TINYINT", "HUGEINT"}
    if expected == "bigint":
        return actual in {"BIGINT", "HUGEINT", "INTEGER"}
    if expected == "number":
        return any(token in actual for token in ("INT", "DECIMAL", "DOUBLE", "FLOAT", "REAL"))
    if expected == "date":
        return actual == "DATE" or actual.startswith("TIMESTAMP")
    return True


def validate_relation(
    con: duckdb.DuckDBPyConnection,
    relation: str,
    contract_path: Path,
    *,
    period_column: str | None = None,
    expected_periods: int | None = None,
    dimensions: dict[str, tuple[str, str]] | None = None,
    strict_columns: bool = True,
) -> int:
    contract = read_contract(contract_path)
    expected_columns = contract_columns(contract)
    description = con.execute(f"DESCRIBE SELECT * FROM {relation}").fetchall()
    actual_columns = [row[0] for row in description]
    if (strict_columns and actual_columns != expected_columns) or (
        not strict_columns and any(column not in actual_columns for column in expected_columns)
    ):
        raise PipelineError(
            f"{contract_path.name}: expected columns {expected_columns}, got {actual_columns}"
        )
    description_by_name = {row[0]: row for row in description}
    for name in expected_columns:
        actual_type = description_by_name[name][1]
        expected_type = contract["schema"][name].get("type")
        if expected_type and not _duck_type_matches(actual_type, expected_type):
            non_null = con.execute(
                f"SELECT COUNT(*) FROM {relation} WHERE \"{name}\" IS NOT NULL"
            ).fetchone()[0]
            if non_null:
                raise PipelineError(
                    f"{contract_path.name}: column {name} expected {expected_type}, got {actual_type}"
                )
        nullable = contract["schema"][name].get("nullable", True)
        if not nullable:
            count = con.execute(
                f"SELECT COUNT(*) FROM {relation} WHERE \"{name}\" IS NULL"
            ).fetchone()[0]
            if count:
                raise PipelineError(f"{contract_path.name}: {count} null values in {name}")
    rows = con.execute(f"SELECT COUNT(*) FROM {relation}").fetchone()[0]
    quality = contract.get("quality", {})
    natural_key = quality.get("natural_key", [])
    duplicate_limit = quality.get("duplicates", {}).get("maximum")
    if natural_key and duplicate_limit is not None:
        key_sql = ", ".join(f'"{column}"' for column in natural_key)
        duplicates = con.execute(
            f"SELECT COUNT(*) FROM (SELECT {key_sql}, COUNT(*) AS n FROM {relation} GROUP BY {key_sql} HAVING n > 1)"
        ).fetchone()[0]
        if duplicates > duplicate_limit:
            raise PipelineError(f"{contract_path.name}: {duplicates} duplicate natural keys")
    if period_column and expected_periods is not None:
        expected_rows = contract.get("volume", {}).get("monthly", {}).get("minimum_rows")
        maximum_rows = contract.get("volume", {}).get("monthly", {}).get("maximum_rows")
        if expected_rows is None or maximum_rows is None or expected_rows != maximum_rows:
            raise PipelineError(f"{contract_path.name}: monthly volume contract is not exact")
        counts = con.execute(
            f"SELECT \"{period_column}\", COUNT(*) FROM {relation} GROUP BY \"{period_column}\""
        ).fetchall()
        if len(counts) != expected_periods or any(count != expected_rows for _, count in counts):
            raise PipelineError(f"{contract_path.name}: monthly volume does not match contract")
    for column, (dimension_relation, dimension_column) in (dimensions or {}).items():
        missing = con.execute(
            f"SELECT COUNT(*) FROM {relation} f LEFT JOIN {dimension_relation} d "
            f"ON f.\"{column}\" = d.\"{dimension_column}\" WHERE d.\"{dimension_column}\" IS NULL"
        ).fetchone()[0]
        if missing:
            raise PipelineError(f"{contract_path.name}: {missing} invalid foreign keys in {column}")
    return rows


def month_id(value: str) -> int:
    year, month = value.split("-")
    return int(year) * 100 + int(month)


def month_text(value: int) -> str:
    return f"{value // 100:04d}-{value % 100:02d}"


def month_range(start: int, end: int) -> list[int]:
    result = []
    year, month = divmod(start, 100)
    while year * 100 + month <= end:
        result.append(year * 100 + month)
        month += 1
        if month == 13:
            year += 1
            month = 1
    return result


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, default=str) + "\n", encoding="utf-8")
