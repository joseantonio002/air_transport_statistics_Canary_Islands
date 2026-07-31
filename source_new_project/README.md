# ISTAC Air Transport Pipeline

This self-contained project extracts monthly ISTAC air-transport data, validates
the contracts, transforms facts, atomically loads both fact tables, and updates
the prediction output.

## Architecture

- `src/pipeline/extract`: streaming ISTAC HTTP extraction with retries.
- `src/pipeline/validation.py`: YAML contract validation.
- `src/pipeline/transform`: airport and territory fact transformations.
- `src/pipeline/pipeline.py`: run/backfill orchestration and atomic loading.
- `src/create_dimensions`: one-time dimension creation.
- `src/model_update`: prediction output generation.
- `airflow/dags`: monthly DockerOperator orchestration.
- `src/update_data`: local visualization automation.

## Prerequisites

Python 3.12 is required for local execution. Docker and Docker Compose are
required for Airflow execution.

```bash
pip install -e '.[test]'
```

## Initialization

From this directory, run `./initialize.sh`. It detects the local timezone,
creates dimensions, builds the pipeline image, starts Compose, waits for
Airflow health, and unpauses the DAG. It does not trigger a pipeline run.
Set `PIPELINE_TIMEZONE` to override the detected timezone.

## Local Commands

```bash
python -m pipeline run
python -m pipeline run --month 2026-06
python -m pipeline backfill --start 2026-01 --end 2026-06
```

The default run fills missing months through the configured latest month. Use
backfill to replace an existing inclusive range.

## Airflow

The `istac_air_transport_pipeline` DAG runs monthly after ISTAC is likely to
have published data. It uses `DockerOperator`, mounts `data`, `config`,
`data_contracts`, and `runtime`, and runs `python -m pipeline run` without a
month argument.

## Visualization Updates

After Airflow completes, run `python src/update_data/main.py`. The automation
requires a clean worktree, verifies Airflow, waits for DAG success, runs
`docs/update_plots.py`, checks HTML outputs, commits with the exact required
message, and pushes to GitHub.

## Configuration

All settings are in `config/config.yaml`. Optional `.env` values and
environment variables override YAML values. Relative paths are resolved from
the project root. Important defaults are five retries, `2004-01` full-history
start, `2099-12` calendar end, and `Atlantic/Canary` timezone.

## Runtime Files

- `data/`: dimensions and monthly facts.
- `data/predictions/Predictions.csv`: model output.
- `runtime/run_metadata/`: one JSON record per pipeline run.
- `runtime/logs/` and `runtime/tmp/`: operational files.

## Troubleshooting

- If Airflow is unavailable, run `docker compose up -d` and wait for health.
- If a month already exists, use `backfill` instead of `run --month`.
- If validation fails, inspect the dataset and contract path in the logged error.
- If a Docker replacement fails, the loader restores both fact tables from backups.

## Tests

```bash
pytest -q
```
