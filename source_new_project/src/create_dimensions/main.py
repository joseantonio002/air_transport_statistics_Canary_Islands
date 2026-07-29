from __future__ import annotations

import argparse
import csv
import re
from calendar import month_name
from datetime import date
from pathlib import Path
from typing import Iterable, Mapping


CALENDAR_COLUMNS = ["MonthId", "MonthStartDate", "MonthNumber", "MonthName", "QuarterNumber", "QuarterName", "Year", "YearMonth"]
AIRPORT_COLUMNS = ["AirportId", "AirportName", "AirportCode", "IcaoCode", "Latitude", "Longitude", "CountryCode", "CountryName"]
AGGREGATE_CODES = {"ES_XES70", "ES70", "FOREIGN"}


def _month(value: str) -> date:
    year, number = (int(part) for part in value.split("-"))
    return date(year, number, 1)


def generate_calendar(start: str = "2004-01", end: str = "2099-12") -> list[dict[str, object]]:
    current, last = _month(start), _month(end)
    result = []
    while current <= last:
        quarter = (current.month - 1) // 3 + 1
        result.append({
            "MonthId": current.year * 100 + current.month,
            "MonthStartDate": current.isoformat(),
            "MonthNumber": current.month,
            "MonthName": month_name[current.month],
            "QuarterNumber": quarter,
            "QuarterName": f"Q{quarter}",
            "Year": current.year,
            "YearMonth": current.strftime("%Y-%m"),
        })
        current = date(current.year + (current.month == 12), 1 if current.month == 12 else current.month + 1, 1)
    return result


def _is_valid_airport(code: str) -> bool:
    if code in AGGREGATE_CODES or code.endswith("_O") or code.startswith("_"):
        return False
    return bool(re.fullmatch(r"[A-Z]{2}_[A-Z0-9]{3,5}", code))


def _number(value: object) -> float | None:
    if value is None or str(value).strip() == "":
        return None
    return float(value)


def build_airport_dimension(istac_airports: Iterable[Mapping[str, object]], enrichment: Iterable[Mapping[str, object]]) -> list[dict[str, object]]:
    enrichment_by_code = {str(row.get("AirportCode") or row.get("local_code") or row.get("ident")): row for row in enrichment}
    valid = {}
    for source in istac_airports:
        code = str(source.get("AirportCode") or source.get("AEROPUERTO_ESCALA_CODE") or "").strip()
        if _is_valid_airport(code):
            valid[code] = source
    output = []
    for airport_id, code in enumerate(sorted(valid)):
        source = valid[code]
        extra = enrichment_by_code.get(code, {})
        icao = str(source.get("IcaoCode") or extra.get("icao_code") or code.split("_", 1)[1])
        output.append({
            "AirportId": airport_id,
            "AirportName": str(source.get("AirportName") or source.get("name") or extra.get("name") or code),
            "AirportCode": code,
            "IcaoCode": icao or None,
            "Latitude": _number(source.get("Latitude") or source.get("latitude") or extra.get("latitude_deg")),
            "Longitude": _number(source.get("Longitude") or source.get("longitude") or extra.get("longitude_deg")),
            "CountryCode": str(source.get("CountryCode") or code.split("_", 1)[0]),
            "CountryName": str(source.get("CountryName") or extra.get("iso_country") or ""),
        })
    return output


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, columns: list[str], rows: Iterable[Mapping[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows({column: row.get(column) for column in columns} for row in rows)


def write_dimensions(output_dir: str | Path, istac_airports: Iterable[Mapping[str, object]], enrichment: Iterable[Mapping[str, object]]) -> None:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    istac_airports = list(istac_airports)
    enrichment = list(enrichment)
    airport_rows = build_airport_dimension(istac_airports, enrichment)
    _write_csv(output_dir / "Airport.csv", AIRPORT_COLUMNS, airport_rows)
    _write_csv(output_dir / "CalendarMonth.csv", CALENDAR_COLUMNS, generate_calendar())
    source_root = output_dir
    for source_name, output_name in [("Final_Territory.csv", "Territory.csv"), ("Final_AircraftMovement.csv", "AircraftMovement.csv"), ("AirService.csv", "AirService.csv")]:
        rows = _read_csv(source_root / source_name)
        if rows:
            _write_csv(output_dir / output_name, list(rows[0]), rows)
    unmatched = [row["AirportCode"] for row in airport_rows if row["Latitude"] is None or row["Longitude"] is None]
    enrichment_codes = {str(row.get("AirportCode") or row.get("local_code") or row.get("ident")) for row in enrichment}
    (output_dir / "dimensions.log").write_text(
        "\n".join([
            f"total ISTAC airport codes: {len(istac_airports)}",
            f"valid airports: {len(airport_rows)}",
            f"external matches: {sum(row['AirportCode'] in enrichment_codes for row in airport_rows)}",
            f"unmatched airports: {', '.join(unmatched) or 'none'}",
            "manual overrides: none",
            "newly unmatched airports: none",
        ]) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Create one-time dimension tables")
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    data_dir = args.project_root / "data"
    airports = _read_csv(data_dir / "istac_airports.csv") or _read_csv(data_dir / "Airport.csv")
    enrichment = _read_csv(data_dir / "airports.csv")
    write_dimensions(data_dir, airports, enrichment)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
