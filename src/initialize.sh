#!/usr/bin/env bash
set -euo pipefail

# The initializer lives under src/, one level below the repository root.
SOURCE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SOURCE_ROOT/.." && pwd)"

if [[ ! -f "$SOURCE_ROOT/.env" ]]; then
  cp "$SOURCE_ROOT/.env.example" "$SOURCE_ROOT/.env"
  echo "Created $SOURCE_ROOT/.env from .env.example"
fi

if [[ ! -S /var/run/docker.sock ]]; then
  echo "ERROR: Docker socket not found at /var/run/docker.sock." >&2
  exit 1
fi

if [[ ! -t 0 ]]; then
  echo "ERROR: initialize.sh requires an interactive terminal to configure AIRFLOW_UID and DOCKER_GID." >&2
  exit 1
fi

DETECTED_AIRFLOW_UID="$(id -u)"
DETECTED_DOCKER_GID="$(stat -c '%g' /var/run/docker.sock)"

read -r -p "Detected AIRFLOW_UID=$DETECTED_AIRFLOW_UID and DOCKER_GID=$DETECTED_DOCKER_GID. Use these values? [Y/n]: " use_detected_ids
use_detected_ids="${use_detected_ids:-Y}"

if [[ "$use_detected_ids" =~ ^[Yy]$ ]]; then
  AIRFLOW_UID="$DETECTED_AIRFLOW_UID"
  DOCKER_GID="$DETECTED_DOCKER_GID"
elif [[ "$use_detected_ids" =~ ^[Nn]$ ]]; then
  while true; do
    read -r -p "Enter AIRFLOW_UID: " AIRFLOW_UID
    [[ "$AIRFLOW_UID" =~ ^[0-9]+$ ]] && break
    echo "AIRFLOW_UID must be a non-negative integer."
  done
  while true; do
    read -r -p "Enter DOCKER_GID: " DOCKER_GID
    [[ "$DOCKER_GID" =~ ^[0-9]+$ ]] && break
    echo "DOCKER_GID must be a non-negative integer."
  done
else
  echo "ERROR: answer Y or N." >&2
  exit 1
fi

export AIRFLOW_UID
export DOCKER_GID
export PIPELINE_IMAGE="${PIPELINE_IMAGE:-istac-air-transport-pipeline:latest}"
export PIPELINE_DATA_DIR="$SOURCE_ROOT/data"
export PIPELINE_CONFIG_DIR="$SOURCE_ROOT/config"
export PIPELINE_CONTRACT_DIR="$SOURCE_ROOT/data_contracts"
export PIPELINE_RUNTIME_DIR="$SOURCE_ROOT/runtime"
export PIPELINE_DOCS_DIR="$PROJECT_ROOT/docs"
export COMPOSE_FILE="$SOURCE_ROOT/compose.yaml"

: "${PIPELINE_IMAGE:?PIPELINE_IMAGE must not be empty}"
echo "Using AIRFLOW_UID=$AIRFLOW_UID and DOCKER_GID=$DOCKER_GID"

COMPOSE_ENV_FILE="$SOURCE_ROOT/runtime/compose.env"
mkdir -p "$SOURCE_ROOT/runtime"
printf '%s\n' \
  "AIRFLOW_UID=$AIRFLOW_UID" \
  "DOCKER_GID=$DOCKER_GID" \
  "PIPELINE_IMAGE=$PIPELINE_IMAGE" \
  "PIPELINE_DATA_DIR=$PIPELINE_DATA_DIR" \
  "PIPELINE_CONFIG_DIR=$PIPELINE_CONFIG_DIR" \
  "PIPELINE_CONTRACT_DIR=$PIPELINE_CONTRACT_DIR" \
  "PIPELINE_RUNTIME_DIR=$PIPELINE_RUNTIME_DIR" \
  "PIPELINE_DOCS_DIR=$PIPELINE_DOCS_DIR" \
  > "$COMPOSE_ENV_FILE"
echo "Saved machine-specific Compose settings to $COMPOSE_ENV_FILE"

cd "$PROJECT_ROOT"
PYTHONPATH=src python -m create_dimensions.main

echo "Building pipeline image"
docker build -f src/Dockerfile -t "$PIPELINE_IMAGE" .
echo "Setting up airflow and executing DAG, this may take a while"
docker compose up -d
