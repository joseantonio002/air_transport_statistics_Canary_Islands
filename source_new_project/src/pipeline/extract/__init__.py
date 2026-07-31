from __future__ import annotations

import csv
import io
import time
from datetime import datetime
from collections.abc import Iterator
from typing import Any
from urllib.parse import urlencode

import requests


class ExtractionError(RuntimeError):
    """Raised when an ISTAC dataset cannot be extracted safely."""


RETRYABLE_STATUSES = {408, 425, 429, 500, 502, 503, 504}


class IstacExtractor:
    def __init__(self, api_base_url: str, datasets: dict[str, str], *, session: Any = None, retries: int = 5, timeout: float = 30, backoff_factor: float = 1) -> None:
        self.api_base_url = api_base_url.rstrip("/")
        self.datasets = datasets
        self.session = session or requests.Session()
        self.retries = retries
        self.timeout = timeout
        self.backoff_factor = backoff_factor

    def _get(self, url: str) -> Any:
        for attempt in range(self.retries + 1):
            try:
                response = self.session.get(url, timeout=self.timeout, stream=True)
            except requests.RequestException as exc:
                if attempt >= self.retries:
                    raise ExtractionError(f"retry exhausted for {url}: {exc}") from exc
                time.sleep(self.backoff_factor * (2**attempt))
                continue
            status = getattr(response, "status_code", 200)
            if status in RETRYABLE_STATUSES:
                if attempt >= self.retries:
                    raise ExtractionError(f"retry exhausted for {url}: HTTP {status}")
                time.sleep(self.backoff_factor * (2**attempt))
                continue
            if status >= 400:
                raise ExtractionError(f"non-retryable HTTP status {status} for {url}")
            return response
        raise ExtractionError(f"retry exhausted for {url}")

    def fetch(self, dataset: str, month: str, required_columns: tuple[str, ...] | None = None) -> Iterator[dict[str, str | None]]:
        if dataset not in self.datasets:
            raise ExtractionError(f"unknown dataset: {dataset}")
        if len(month) != 7 or month[4] != "-" or not month.replace("-", "").isdigit():
            raise ExtractionError(f"invalid month: {month}")
        query = urlencode({"lang": "en", "representation": f"TIME_PERIOD[{month}]", "granularity": "TIME_PERIOD[M]"})
        url = f"{self.api_base_url}/datasets/ISTAC/{self.datasets[dataset]}/~latest.csv?{query}"
        response = self._get(url)
        try:
            lines = response.iter_lines(decode_unicode=True)
            text = "\n".join(line.decode() if isinstance(line, bytes) else line for line in lines)
            reader = csv.DictReader(io.StringIO(text), strict=True)
            columns = reader.fieldnames or []
            if not columns or any(column is None or not str(column).strip() for column in columns):
                raise ExtractionError(f"malformed CSV response for dataset {dataset}")
            required = required_columns or ("TIME_PERIOD_CODE", "OBS_VALUE")
            missing = [column for column in required if column not in columns]
            if missing:
                raise ExtractionError(f"missing required columns for dataset {dataset}: {missing}")
            for row in reader:
                if None in row:
                    raise ExtractionError(f"malformed CSV response for dataset {dataset}")
                period = row.get("TIME_PERIOD_CODE") or row.get("TIME_PERIOD")
                if period and _normalise_month(period) != month:
                    continue
                if "OBS_VALUE" in row and (row["OBS_VALUE"] is None or row["OBS_VALUE"].strip() == ""):
                    row["OBS_VALUE"] = None
                if "AEROPUERTO_ORIGEN_DESTINO_CODE" in row:
                    row["AEROPUERTO_ESCALA_CODE"] = row["AEROPUERTO_ORIGEN_DESTINO_CODE"]
                yield row
        except csv.Error as exc:
            raise ExtractionError(f"malformed CSV response for dataset {dataset}: {exc}") from exc


def _normalise_month(value: str) -> str:
    value = value.strip()
    if len(value) == 7 and value[4] == "-":
        return value
    if len(value) == 8 and value[4] == "-" and value[5] == "M":
        return f"{value[:4]}-{value[6:]}"
    for pattern in ("%m/%Y", "%Y/%m", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, pattern).strftime("%Y-%m")
        except ValueError:
            continue
    return value
