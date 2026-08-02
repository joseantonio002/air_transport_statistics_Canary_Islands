from __future__ import annotations

import logging
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from air_transport_statistics.load_config.config import load_config

from .common import AlreadyUpToDateError, write_json
from .extraction import extract
from .load import load, validate_existing
from .transform import transform


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def _logger(run_id: str, path: Path) -> logging.Logger:
    path.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("air_transport_statistics.pipeline")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    file_handler = logging.FileHandler(path, encoding="utf-8")
    file_handler.setFormatter(formatter)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
    return logger


def run() -> int:
    config = load_config()
    run_id = uuid.uuid4().hex
    log_path = config.paths.logs / f"pipeline-{run_id}.log"
    logger = _logger(run_id, log_path)
    metadata = {
        "run_id": run_id,
        "mode": None,
        "requested_period": {"start": None, "end": None},
        "status": "running",
        "rows_received": {},
        "rows_inserted_or_replaced": {},
        "start_timestamp": _timestamp(),
        "finish_timestamp": None,
        "error_type": None,
        "error_message": None,
        "log_path": str(log_path),
    }
    metadata_path = config.paths.metadata / f"{run_id}.json"
    database_path = config.paths.temporary / f"{run_id}.duckdb"
    try:
        airport_path = config.paths.data / "TrafficPerAirport.csv"
        territory_path = config.paths.data / "TrafficPerTerritory.csv"
        initial = not airport_path.is_file() or not territory_path.is_file()
        metadata["mode"] = "initial" if initial else "incremental"
        local_latest = None if initial else validate_existing(config, airport_path, territory_path)
        logger.info("Starting %s pipeline", metadata["mode"])
        extracted = extract(
            config,
            config.paths.contracts / "ingestion_data_contracts",
            config.paths.temporary,
            run_id,
            local_latest,
        )
        metadata["requested_period"] = {
            "start": extracted.start_month,
            "end": extracted.end_month,
        }
        metadata["rows_received"] = extracted.rows_received
        transformed = transform(
            config,
            extracted,
            database_path,
            None if initial else airport_path,
            None if initial else territory_path,
        )
        metadata["rows_inserted_or_replaced"] = transformed.rows_inserted_or_replaced
        loaded_rows = load(config, transformed, extracted.start_month, extracted.end_month)
        metadata["rows_inserted_or_replaced"] = loaded_rows | transformed.rows_inserted_or_replaced
        metadata["status"] = "success"
        logger.info("Pipeline completed successfully")
        return 0
    except Exception as exc:
        metadata["status"] = "failed"
        metadata["error_type"] = type(exc).__name__
        metadata["error_message"] = str(exc)
        if isinstance(exc, AlreadyUpToDateError):
            logger.error("Pipeline is already up to date: %s", exc)
        else:
            logger.exception("Pipeline failed")
        return 1
    finally:
        metadata["finish_timestamp"] = _timestamp()
        write_json(metadata_path, metadata)
        if metadata["status"] == "success":
            database_path.unlink(missing_ok=True)
            database_path.with_suffix(".duckdb.wal").unlink(missing_ok=True)


def main() -> int:
    return run()


if __name__ == "__main__":
    sys.exit(main())
