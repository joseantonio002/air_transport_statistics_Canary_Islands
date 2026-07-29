from __future__ import annotations

import csv
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any


class ModelUpdateError(ValueError):
    """Raised when model inputs are missing or invalid."""


def month_id_to_date(month_id: int | str) -> str:
    text = str(month_id)
    if len(text) != 6 or not text.isdigit() or not 1 <= int(text[4:]) <= 12:
        raise ModelUpdateError(f"invalid MonthId: {month_id}")
    return f"{text[:4]}-{text[4:]}-01"


def _next_month(year: int, month: int) -> tuple[int, int]:
    return (year + 1, 1) if month == 12 else (year, month + 1)


def _read(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise ModelUpdateError(f"missing input: {path.name}")
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def update_predictions(data_dir: str | Path) -> list[dict[str, Any]]:
    data_dir = Path(data_dir)
    facts = _read(data_dir / "TrafficPerTerritory.csv")
    territories = _read(data_dir / "Territory.csv")
    territory_names = {int(row["TerritoryId"]): row["TerritoryName"] for row in territories}
    if not territory_names:
        raise ModelUpdateError("Territory.csv has no dimension rows")
    grouped: dict[int, dict[int, int | float]] = defaultdict(lambda: defaultdict(int))
    for row in facts:
        required = {"IslandId", "AirServiceId", "AircraftMovementId", "MonthId", "Passengers"}
        missing = required - row.keys()
        if missing:
            raise ModelUpdateError(f"fact schema missing columns: {sorted(missing)}")
        if row["AirServiceId"] != "0" or row["AircraftMovementId"] != "2":
            continue
        island = int(row["IslandId"])
        month = int(row["MonthId"])
        month_id_to_date(month)
        value = 0 if row["Passengers"].strip() == "" else float(row["Passengers"])
        grouped[island][month] += int(value) if value.is_integer() else value
    output: list[dict[str, Any]] = []
    for island_id in sorted(grouped):
        observed = grouped[island_id]
        months = sorted(observed)
        if island_id not in territory_names:
            raise ModelUpdateError(f"missing territory dimension for IslandId {island_id}")
        last_year, last_month = (int(str(months[-1])[:4]), int(str(months[-1])[4:]))
        all_months = months[:]
        for _ in range(12):
            last_year, last_month = _next_month(last_year, last_month)
            all_months.append(last_year * 100 + last_month)
        baseline = observed[months[-1]]
        for month in all_months:
            real = observed.get(month)
            output.append({
                "Island": territory_names[island_id],
                "Month": month_id_to_date(month),
                "RealPassengers": real,
                "yhat_lower": baseline,
                "yhat": baseline,
                "yhat_upper": baseline,
            })
    output_path = data_dir / "predictions" / "Predictions.csv"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    columns = ["Island", "Month", "RealPassengers", "yhat_lower", "yhat", "yhat_upper"]
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(output)
    return output


def main() -> int:
    update_predictions(Path.cwd() / "data")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
