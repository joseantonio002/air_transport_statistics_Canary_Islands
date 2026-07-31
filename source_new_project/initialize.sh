#!/usr/bin/env bash
set -euo pipefail

# The initializer lives at the project root, alongside src/, config/, and compose.yaml.
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TIMEZONE="${PIPELINE_TIMEZONE:-$(cat /etc/timezone 2>/dev/null || true)}"
TIMEZONE="${TIMEZONE:-Atlantic/Canary}"
export PIPELINE_TIMEZONE="$TIMEZONE"
echo "Using timezone: $TIMEZONE"

cd "$PROJECT_ROOT"
PYTHONPATH=src python -m create_dimensions.main --project-root "$PROJECT_ROOT"
docker build -f src/Dockerfile -t "${PIPELINE_IMAGE:-istac-air-transport-pipeline:latest}" .
docker compose up -d

until curl --fail --silent http://localhost:8080/api/v2/monitor/health >/dev/null; do
  sleep 5
done
echo "Airflow is ready. Manual commands:"
echo "  PYTHONPATH=src python -m pipeline run"
echo "  PYTHONPATH=src python -m pipeline backfill --start 2026-01 --end 2026-06"
