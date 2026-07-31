from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from create_dimensions.main import _read_csv
from model_update.main import update_predictions

from .config import Config, load_config
from .extract import IstacExtractor
from .pipeline import run_pipeline
from .transform import transform_traffic_per_airport, transform_traffic_per_territory
from .validation import validate_records


AIRPORT_CONTRACTS = {
    "airport_total_passengers": "total_passengers.yaml",
    "airport_total_goods_mail": "total_goods_mails.yaml",
    "airport_total_operations": "total_operations.yaml",
    "airport_arrival_passengers": "arrival_passengers.yaml",
    "airport_arrival_goods_mail": "arrival_goods_mails.yaml",
    "airport_arrival_operations": "arrival_operations.yaml",
    "airport_departure_passengers": "departure_passengers.yaml",
    "airport_departure_goods_mail": "departure_goods_mails.yaml",
    "airport_departure_operations": "departure_operations.yaml",
    "territory_passengers": "C00017A_000013.yaml",
    "territory_goods_mail": "C00017A_000014.yaml",
    "territory_operations": "C00017A_000015.yaml",
}


def _month_text(month_id: int) -> str:
    return f"{month_id // 100:04d}-{month_id % 100:02d}"


def _dimension_map(path: Path, code: str, identifier: str) -> dict[str, int]:
    with path.open(newline="", encoding="utf-8") as handle:
        return {str(row[code]): int(row[identifier]) for row in csv.DictReader(handle)}


class PipelineApplication:
    def __init__(self, config: Config, extractor: IstacExtractor | None = None) -> None:
        self.config = config
        self.data_dir = config.paths.data
        self.contract_dir = config.paths.contracts / "ingestion_data_contracts"
        self.extractor = extractor or IstacExtractor(
            config.source.api_base_url,
            config.source.datasets,
            retries=config.retry_count,
            timeout=config.request_timeout,
            backoff_factor=config.backoff_factor,
        )
        self.airports = _dimension_map(self.data_dir / "Airport.csv", "AirportCode", "AirportId")
        self.services = _dimension_map(self.data_dir / "AirService.csv", "AirServiceCode", "AirServiceId")
        self.movements = _dimension_map(self.data_dir / "AircraftMovement.csv", "AircraftMovementCode", "AircraftMovementId")
        self.territories = _dimension_map(self.data_dir / "Territory.csv", "TerritoryCode", "TerritoryId")

    def _fetch(self, dataset: str, month: str) -> list[dict[str, str | None]]:
        records = list(self.extractor.fetch(dataset, month))
        contract_name = AIRPORT_CONTRACTS[dataset]
        validate_records(records, self.contract_dir / contract_name)
        return records

    def build_month(self, month_id: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        month = _month_text(month_id)
        airport_passengers: list[dict[str, Any]] = []
        airport_goods: list[dict[str, Any]] = []
        airport_operations: list[dict[str, Any]] = []
        for suffix in ("total", "arrival", "departure"):
            airport_passengers.extend(self._fetch(f"airport_{suffix}_passengers", month))
            airport_goods.extend(self._fetch(f"airport_{suffix}_goods_mail", month))
            airport_operations.extend(self._fetch(f"airport_{suffix}_operations", month))
        territory_passengers = self._fetch("territory_passengers", month)
        territory_goods = self._fetch("territory_goods_mail", month)
        territory_operations = self._fetch("territory_operations", month)
        airport_facts = transform_traffic_per_airport(
            airport_passengers,
            airport_goods,
            airport_operations,
            [{"AirportCode": code, "AirportId": identifier} for code, identifier in self.airports.items()],
            self.services,
            self.movements,
            month_id,
        )
        territory_facts = transform_traffic_per_territory(
            territory_passengers,
            territory_goods,
            territory_operations,
            self.territories,
            self.services,
            self.movements,
            month_id,
        )
        return airport_facts, territory_facts

    def run(self, mode: str, *, month: str | None = None, start: str | None = None, end: str | None = None) -> dict[str, Any]:
        return run_pipeline(
            self.data_dir,
            mode,
            self.build_month,
            latest_month=self.config.latest_available_month,
            model_update=lambda: update_predictions(self.data_dir),
            start=month if mode == "run" else start,
            end=end,
        )


def run_from_project_root(project_root: str | Path, mode: str, *, month: str | None = None, start: str | None = None, end: str | None = None) -> dict[str, Any]:
    return PipelineApplication(load_config(project_root)).run(mode, month=month, start=start, end=end)
