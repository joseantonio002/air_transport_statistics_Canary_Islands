from __future__ import annotations

import logging
import time
import uuid
from pathlib import Path

import duckdb
import requests

from .common import (
    AlreadyUpToDateError,
    ExtractedFile,
    ExtractionResult,
    PipelineError,
    month_id,
    month_range,
    month_text,
    relation_for_csv,
    sql_path,
    validate_relation,
)

LOGGER = logging.getLogger(__name__)
DOWNLOAD_DELAY_SECONDS = 1.0

AIRPORT_DATASETS = {
    "total_passengers": "airport_total_passengers",
    "total_goods_mails": "airport_total_goods_mail",
    "total_operations": "airport_total_operations",
    "arrival_passengers": "airport_arrival_passengers",
    "arrival_goods_mails": "airport_arrival_goods_mail",
    "arrival_operations": "airport_arrival_operations",
    "departure_passengers": "airport_departure_passengers",
    "departure_goods_mails": "airport_departure_goods_mail",
    "departure_operations": "airport_departure_operations",
}
TERRITORY_DATASETS = {
    "territory_passengers": "territory_passengers",
    "territory_goods_mails": "territory_goods_mail",
    "territory_operations": "territory_operations",
}


def _download(url: str, path: Path, retries: int, timeout: float, backoff: float) -> None:
    print(f"Trying to download data from {url}")
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            with requests.get(url, stream=True, timeout=timeout) as response:
                if response.status_code >= 500 or response.status_code == 429:
                    response.raise_for_status()
                response.raise_for_status()
                with path.open("wb") as output:
                    for chunk in response.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            output.write(chunk)
            time.sleep(DOWNLOAD_DELAY_SECONDS)
            return
        except requests.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else None
            if status is not None and 400 <= status < 500 and status != 429:
                raise PipelineError(f"failed to download {url}: HTTP {status}") from exc
            last_error = exc
            if attempt == retries:
                break
            delay = backoff * (2**attempt)
            LOGGER.warning("Download failed, retrying in %.1f seconds: %s", delay, exc)
            time.sleep(delay)
        except (requests.RequestException, OSError) as exc:
            last_error = exc
            if attempt == retries:
                break
            delay = backoff * (2**attempt)
            LOGGER.warning("Download failed, retrying in %.1f seconds: %s", delay, exc)
            time.sleep(delay)
    raise PipelineError(f"failed to download {url}: {last_error}") from last_error


def _url(base_url: str, dataset_id: str, start: str | None, end: str | None) -> str:
    endpoint = f"{base_url.rstrip('/')}/datasets/ISTAC/{dataset_id}/~latest.csv"
    if start is None:
        representation = "TIME_PERIOD[~last=1]"
    elif start == "2004-01":
        representation = "TIME_PERIOD[~after=2004-M01]"
    else:
        representation = f"TIME_PERIOD[~range={start.replace('-', '-M')};{end.replace('-', '-M')}]"
    return f"{endpoint}?representation={representation}&granularity=TIME_PERIOD[M]&lang=en"


def _max_month(path: Path) -> int:
    with duckdb.connect() as con:
        value = con.execute(
            f"SELECT MAX(TRY_CAST(REPLACE(TIME_PERIOD_CODE, '-M', '') AS INTEGER)) FROM {relation_for_csv(path)}"
        ).fetchone()[0]
    if value is None:
        raise PipelineError(f"downloaded dataset has no periods: {path.name}")
    return value


def discover_latest(config: object, dataset_id: str, temporary_dir: Path) -> int:
    path = temporary_dir / f"latest-{dataset_id}-{uuid.uuid4().hex}.csv"
    try:
        _download(
            _url(config.source.api_base_url, dataset_id, None, None),
            path,
            config.retry_count,
            config.request_timeout,
            config.backoff_factor,
        )
        return _max_month(path)
    finally:
        path.unlink(missing_ok=True)


def _extract_group(
    config: object,
    contract_dir: Path,
    temporary_dir: Path,
    datasets: dict[str, str],
    start: int,
    end: int,
    run_id: str,
) -> tuple[dict[str, ExtractedFile], int, int]:
    files: dict[str, ExtractedFile] = {}
    actual_start: int | None = None
    actual_end: int | None = None
    requested_start = month_text(start) if start > 190001 else "1900-01"
    requested_end = month_text(end) if end else None
    for contract_name, config_key in datasets.items():
        dataset_id = config.source.datasets[config_key]
        path = temporary_dir / f"{run_id}-{contract_name}.csv"
        url = _url(config.source.api_base_url, dataset_id, requested_start, requested_end)
        LOGGER.info("Downloading %s (%s)", contract_name, url)
        _download(url, path, config.retry_count, config.request_timeout, config.backoff_factor)
        contract = contract_dir / f"{contract_name}.yaml"
        if not contract.is_file():
            contract = contract_dir / f"{dataset_id}.yaml"
        with duckdb.connect() as con:
            relation = relation_for_csv(path)
            count = validate_relation(
                con, relation, contract, period_column="TIME_PERIOD_CODE", strict_columns=False
            )
            min_value, max_value = con.execute(
                f"SELECT MIN(TRY_CAST(REPLACE(TIME_PERIOD_CODE, '-M', '') AS INTEGER)), "
                f"MAX(TRY_CAST(REPLACE(TIME_PERIOD_CODE, '-M', '') AS INTEGER)) FROM {relation}"
            ).fetchone()
            if min_value is None or max_value is None:
                raise PipelineError(f"{contract_name}: no data returned")
            file_start = min_value
            file_end = max_value
            expected_periods = len(month_range(file_start, file_end))
            validate_relation(
                con,
                relation,
                contract,
                period_column="TIME_PERIOD_CODE",
                expected_periods=expected_periods,
                strict_columns=False,
            )
        actual_start = file_start if actual_start is None else min(actual_start, file_start)
        actual_end = file_end if actual_end is None else max(actual_end, file_end)
        files[contract_name] = ExtractedFile(contract_name, dataset_id, path, count)
    if actual_start is None or actual_end is None:
        raise PipelineError("no datasets were extracted")
    return files, actual_start, actual_end


def extract(config: object, contract_dir: Path, temporary_dir: Path, run_id: str, local_latest: int | None) -> ExtractionResult:
    temporary_dir.mkdir(parents=True, exist_ok=True)
    airport_latest = discover_latest(config, config.source.datasets["airport_total_passengers"], temporary_dir)
    territory_latest = discover_latest(config, config.source.datasets["territory_passengers"], temporary_dir)
    if airport_latest != territory_latest:
        raise PipelineError(f"airport and territory latest months differ: {airport_latest} vs {territory_latest}")
    latest = airport_latest
    if local_latest is not None and local_latest >= latest:
        raise AlreadyUpToDateError(f"no new data: local month {local_latest}, ISTAC month {latest}")
    start = local_latest + 1 if local_latest is not None else 200401
    airport_files, airport_start, airport_end = _extract_group(
        config, contract_dir, temporary_dir, AIRPORT_DATASETS, start, latest, run_id
    )
    territory_files, territory_start, territory_end = _extract_group(
        config, contract_dir, temporary_dir, TERRITORY_DATASETS, start, latest, run_id
    )
    actual_start = min(airport_start, territory_start)
    actual_end = max(airport_end, territory_end)
    return ExtractionResult(
        files={**airport_files, **territory_files},
        start_month=month_text(actual_start),
        end_month=month_text(actual_end),
        latest_month=month_text(latest),
        rows_received={name: file.rows for name, file in {**airport_files, **territory_files}.items()},
    )
