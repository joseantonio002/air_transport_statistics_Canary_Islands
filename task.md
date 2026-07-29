# TASK.md — ISTAC Pipeline Rewrite

This file is the single source of truth for executing the work sequentially in OpenCode.

## Execution Protocol

1. Read this entire file before modifying any code.
2. Execute tasks strictly in numerical order. Do not start a task until the previous task has been completed and verified.
3. When starting a task, change its checkbox in **Progress** from `[ ]` to `[-]`.
4. Work test-first according to the common instructions. Confirm that new tests fail for the expected reason before implementing.
5. When a task is finished, run its verification steps, complete its **Completion Record**, and change its checkbox to `[x]`.
6. Continue automatically to the next task once the current task has been fully verified.
7. Stop only for a genuine blocker, a required human decision, a risk of data loss, missing credentials, or an unauthorized irreversible action.
8. Do not mark a task as complete if tests are still failing because of changes made in that task.
9. Do not alter earlier requirements to make later tasks easier. If you identify a contradiction, document the conflict and stop.
10. Before any commit, push, deployment, broad deletion, or modification of the old project, request explicit approval.

## Progress

- [x] **Task 1:** [Establish Contracts And Project Foundation](#task-1--establish-contracts-and-project-foundation)
- [x] **Task 2:** [Correct And Validate Data Contracts](#task-2--correct-and-validate-data-contracts)
- [x] **Task 3:** [Implement Contract Validation](#task-3--implement-contract-validation)
- [x] **Task 4:** [Create Dimension Tables](#task-4--create-dimension-tables)
- [x] **Task 5:** [Implement API Extraction](#task-5--implement-api-extraction)
- [x] **Task 6:** [Implement Airport And Territory Transformations](#task-6--implement-airport-and-territory-transformations)
- [x] **Task 7:** [Implement Pipeline Modes And Atomic Loading](#task-7--implement-pipeline-modes-and-atomic-loading)
- [x] **Task 8:** [Implement Model Update](#task-8--implement-model-update)
- [x] **Task 9:** [Docker, Airflow, And Initialization](#task-9--docker-airflow-and-initialization)
- [x] **Task 10:** [Visualization Automation](#task-10--visualization-automation)
- [x] **Task 11:** [Full Integration And Final Cleanup](#task-11--full-integration-and-final-cleanup)

## Common Instructions

Work test-first.

Before implementing anything:

1. Inspect the existing project and relevant files.
2. Identify the exact behavior to implement.
3. Write tests for that behavior first.
4. Run the tests and confirm they fail for the expected reason.
5. Implement the smallest correct solution.
6. Run the targeted tests.
7. Run the full test suite when appropriate.
8. Do not weaken tests merely to make them pass.
9. Do not implement behavior outside this prompt.
10. Report files changed, tests run, and any unresolved questions.

Use pytest. Prefer DuckDB or Polars over pandas because the fact tables are large. Do not load complete historical datasets into Python memory. Use streaming downloads and DuckDB relations where possible.

All paths must work both:
- from the repository source checkout;
- after moving the contents of `source_new_project/` to the repository root.

Do not modify the old project unless explicitly requested. New implementation belongs inside `source_new_project/`.

## Global Definition of Done

- [ ] All tasks 1–11 are marked as complete.
- [ ] All unit, integration, and contract tests pass.
- [ ] The Docker image builds successfully.
- [ ] The Airflow DAG imports successfully and its configuration has been verified.
- [ ] The CLI commands and documentation match the implemented behavior.
- [ ] `source_new_project/` is self-contained and can be moved to the repository root.
- [ ] The old project remains unchanged.

## Task 1 — Establish Contracts And Project Foundation

**Status:** complete

Prepare the new project foundation inside `source_new_project/`.

Inspect the existing investigation results and contracts before changing anything.

The project must use this package structure:

source_new_project/
├── pyproject.toml
├── README.md
├── .gitignore
├── .env.example
├── compose.yaml
├── airflow/
├── docs/
├── src/
│   ├── pipeline/
│   ├── create_dimensions/
│   └── model_update/
├── data_contracts/
├── data/
├── config/
├── runtime/
└── tests/

The Python package must be called `pipeline`, so these commands must work:

python -m pipeline run
python -m pipeline run --month 2026-06
python -m pipeline backfill --start 2026-01 --end 2026-06

Create the initial pytest configuration and test layout.

Implement configuration loading with:

- YAML configuration from `config/config.yaml`;
- optional `.env` support;
- environment-variable overrides;
- paths resolved relative to the project root;
- configuration usable both locally and inside Docker;
- no hardcoded host-specific absolute paths.

Put all pipeline configuration in `config/config.yaml`, including:

- source API URLs and dataset IDs;
- data, contract, logs, metadata, and temporary paths;
- retry count, default `5`;
- request timeout;
- pipeline timeout;
- backoff settings;
- full-history start month, `2004-01`;
- calendar end month, `2099-12`;
- Airflow timezone settings.

Use the investigation findings as baseline facts:

- ISTAC latest available month: `2026-06`;
- monthly source range: `2004-01` through `2026-06`;
- TrafficPerAirport baseline: `17,164` rows/month;
- TrafficPerTerritory baseline: `480` rows/month.

Before implementation, add tests for configuration loading, path resolution, defaults, environment overrides, and invalid configuration.

Then implement and verify.

### Completion Checklist

- [x] Relevant code and contracts were inspected before implementation.
- [x] The required tests were written first.
- [x] The initial failure was confirmed for the expected reason.
- [x] The smallest correct solution compatible with this task was implemented.
- [x] The targeted tests for this task pass.
- [x] The appropriate broader test suite was run and the result was recorded.
- [x] No tests were weakened and no out-of-scope behavior was added.
- [x] The corresponding checkbox in **Progress** was updated.

### Completion Record

- **Files changed:** `source_new_project/pyproject.toml`, `source_new_project/src/pipeline/`, `source_new_project/src/create_dimensions/`, `source_new_project/src/model_update/`, `source_new_project/config/config.yaml`, `source_new_project/README.md`, `source_new_project/.gitignore`, `source_new_project/runtime/.gitkeep`, `source_new_project/tests/`, `task.md`.
- **Tests added/modified:** `source_new_project/tests/conftest.py`, `source_new_project/tests/test_config.py`.
- **Commands run:** `pytest -q tests/test_config.py`; `PYTHONPATH=src python -m pipeline --help`; `PYTHONPATH=src python -m pipeline run --month 2026-06`; `PYTHONPATH=src python -m pipeline backfill --start 2026-01 --end 2026-06`; `pytest -q`.
- **Results:** 3 targeted tests passed; full suite 3 passed; all CLI smoke commands exited successfully.
- **Decisions and assumptions:** Configuration uses a small dependency-free `.env` parser, environment variables take precedence over `.env`, and relative paths resolve from the supplied project root.
- **Unresolved questions:** none

## Task 2 — Correct And Validate Data Contracts

**Status:** complete

Review every YAML file under `source_new_project/data_contracts/`.

Make the contracts executable and consistent with the actual project.

Required decisions:

- Use `output_data_contracts`, not the misspelled `ouptut_data_contracts`.
- Use clean filenames:
  - Airport.csv
  - Territory.csv
  - AircraftMovement.csv
  - AirService.csv
  - CalendarMonth.csv
  - TrafficPerAirport.csv
  - TrafficPerTerritory.csv
- Airport coordinates may be null.
- AirportCode is required.
- Include IcaoCode in the airport contract if it is part of the final schema.
- Territory columns are:
  - TerritoryId
  - TerritoryCode
  - TerritoryName
- Fact tables use MonthId, not a date column.
- Fact duplicate validation uses natural keys.
- Foreign-key relationships must be validated.
- Extra source columns are allowed.
- Missing required columns fail validation.
- Null and schema violations fail.
- Source monthly row counts must match the investigated values.
- Output monthly row counts are:
  - TrafficPerAirport: exactly `17,164` baseline rows/month.
  - TrafficPerTerritory: exactly `480` baseline rows/month.
- Add contracts for the three territory ingestion datasets:
  - C00017A_000013
  - C00017A_000014
  - C00017A_000015

Write tests first for:
- YAML parsing;
- required contract fields;
- schema definitions;
- nullable fields;
- natural keys;
- foreign keys;
- exact monthly volumes;
- all contract paths.

Then correct the contracts and verify all tests.

### Completion Checklist

- [x] Relevant code and contracts were inspected before implementation.
- [x] The required tests were written first.
- [x] The initial failure was confirmed for the expected reason.
- [x] The smallest correct solution compatible with this task was implemented.
- [x] The targeted tests for this task pass.
- [x] The appropriate broader test suite was run and the result was recorded.
- [x] No tests were weakened and no out-of-scope behavior was added.
- [x] The corresponding checkbox in **Progress** was updated.

### Completion Record

- **Files changed:** `source_new_project/data_contracts/output_data_contracts/airport.yaml`, `territory.yaml`, `aircraft_movement.yaml`, `traffic_per_airport.yaml`, `traffic_per_territory.yaml`, and three new territory ingestion contracts.
- **Tests added/modified:** `source_new_project/tests/test_contracts.py`.
- **Commands run:** `pytest -q tests/test_contracts.py`; `pytest -q`.
- **Results:** Contract tests 7 passed; full suite 10 passed.
- **Decisions and assumptions:** Canonical output filenames are represented by contract source paths; territory ingestion contracts use the shared territory natural key and the investigated 480-row monthly baseline.
- **Unresolved questions:** none

## Task 3 — Implement Contract Validation

**Status:** complete

Implement reusable contract validation for CSV/API datasets using DuckDB or Polars.

The validator must check:

- required columns;
- data types;
- nullability;
- duplicate natural keys;
- expected row counts;
- foreign-key relationships;
- invalid or missing dates/months;
- unexpected missing source datasets;
- representative bad-row samples, capped at 20 rows per failure.

Validation errors must:
- use clear exception types;
- include dataset name and contract path;
- include failing column/key information;
- be logged;
- fail the pipeline.

Write tests first using small CSV fixtures for every validation rule, including passing and failing cases.

Then implement the validator and run both unit tests and contract tests against available project data.

### Completion Checklist

- [x] Relevant code and contracts were inspected before implementation.
- [x] The required tests were written first.
- [x] The initial failure was confirmed for the expected reason.
- [x] The smallest correct solution compatible with this task was implemented.
- [x] The targeted tests for this task pass.
- [x] The appropriate broader test suite was run and the result was recorded.
- [x] No tests were weakened and no out-of-scope behavior was added.
- [x] The corresponding checkbox in **Progress** was updated.

### Completion Record

- **Files changed:** `source_new_project/src/pipeline/validation.py`.
- **Tests added/modified:** `source_new_project/tests/test_validation.py`.
- **Commands run:** `pytest -q tests/test_validation.py`; `pytest -q`.
- **Results:** Validator tests 7 passed; full suite 17 passed.
- **Decisions and assumptions:** Validation accepts extra source columns, reports up to 20 failing rows, and resolves foreign-key references by contract dataset name.
- **Unresolved questions:** none

## Task 4 — Create Dimension Tables

**Status:** complete

Rewrite the old dimension notebook into:

source_new_project/src/create_dimensions/main.py

This is a one-time initialization command.

Create:

- Airport.csv
- Territory.csv
- AircraftMovement.csv
- AirService.csv
- CalendarMonth.csv

CalendarMonth must contain exactly:

- MonthId
- MonthStartDate
- MonthNumber
- MonthName
- QuarterNumber
- QuarterName
- Year
- YearMonth

Generate months from `2004-01` through `2099-12`, inclusive.

Use `MonthId = YYYYMM`.

Airport requirements:

- Build primarily from the complete valid ISTAC airport set.
- Preserve ISTAC AirportCode as the canonical key.
- Preserve ISTAC airport name.
- Derive IcaoCode from codes such as `GB_EGPF`.
- Use `airports.csv` only for enrichment.
- Never remove a valid ISTAC airport because enrichment is unavailable.
- Latitude and Longitude may be null.
- Preserve unmatched airports:
  - DE_EDDT
  - GB_EGCN
- Exclude aggregate codes using the investigated rules:
  - country codes;
  - autonomous-community aggregates;
  - island aggregates;
  - `_O` categories;
  - `ES_XES70`;
  - `ES70`;
  - `FOREIGN`.

Write a plain-text log containing:

- total ISTAC airport codes;
- valid airports;
- external matches;
- unmatched airports;
- manual overrides;
- newly unmatched airports.

Do not create run_metadata for this one-time step.

Write tests first for:
- calendar boundaries and row count `1152`;
- MonthId generation;
- airport aggregate filtering;
- ISTAC airport preservation;
- unmatched airport preservation;
- nullable coordinates;
- deterministic dimension output;
- dimension schemas;
- existing known airport matches.

Then implement and verify.

### Completion Checklist

- [x] Relevant code and contracts were inspected before implementation.
- [x] The required tests were written first.
- [x] The initial failure was confirmed for the expected reason.
- [x] The smallest correct solution compatible with this task was implemented.
- [x] The targeted tests for this task pass.
- [x] The appropriate broader test suite was run and the result was recorded.
- [x] No tests were weakened and no out-of-scope behavior was added.
- [x] The corresponding checkbox in **Progress** was updated.

### Completion Record

- **Files changed:** `source_new_project/src/create_dimensions/main.py`, generated dimension CSVs under `source_new_project/data/`, and `source_new_project/data/dimensions.log`.
- **Tests added/modified:** `source_new_project/tests/test_dimensions.py`.
- **Commands run:** `pytest -q tests/test_dimensions.py`; `PYTHONPATH=src python -m create_dimensions.main --project-root .`; `pytest -q`.
- **Results:** Dimension tests 4 passed; full suite 21 passed; initializer completed and generated 1,152 calendar rows.
- **Decisions and assumptions:** The initializer uses `data/istac_airports.csv` when available, falls back to the baseline airport input, and uses `airports.csv` only for optional enrichment.
- **Unresolved questions:** none

## Task 5 — Implement API Extraction

**Status:** complete

Implement streaming ISTAC extraction under:

src/pipeline/extract/

Use `requests`.

Requirements:

- Retry network errors and retryable HTTP statuses.
- Default maximum retries: `5`.
- Exponential backoff.
- Configurable request timeout.
- Do not save raw API data during normal pipeline runs.
- Do not load complete datasets into Python memory.
- Use monthly filtering explicitly.
- Never include annual rows when processing monthly facts.
- Support fetching:
  - airport passengers;
  - airport goods/mail;
  - airport operations;
  - territory passengers;
  - territory goods/mail;
  - territory operations.

Normalize source differences, especially:

- operation datasets use `AEROPUERTO_ORIGEN_DESTINO_CODE`;
- passenger/goods datasets use `AEROPUERTO_ESCALA_CODE`.

Write tests first using mocked responses for:

- successful extraction;
- malformed responses;
- timeout;
- retryable status;
- non-retryable status;
- retry exhaustion;
- monthly filtering;
- null OBS_VALUE;
- extra source columns;
- missing required columns.

Then implement and verify.

### Completion Checklist

- [x] Relevant code and contracts were inspected before implementation.
- [x] The required tests were written first.
- [x] The initial failure was confirmed for the expected reason.
- [x] The smallest correct solution compatible with this task was implemented.
- [x] The targeted tests for this task pass.
- [x] The appropriate broader test suite was run and the result was recorded.
- [x] No tests were weakened and no out-of-scope behavior was added.
- [x] The corresponding checkbox in **Progress** was updated.

### Completion Record

- **Files changed:** `source_new_project/src/pipeline/extract/__init__.py`.
- **Tests added/modified:** `source_new_project/tests/test_extraction.py`.
- **Commands run:** `pytest -q tests/test_extraction.py`; `pytest -q`.
- **Results:** Extraction tests 5 passed; full suite 26 passed.
- **Decisions and assumptions:** Extraction returns streaming row iterators, keeps raw payloads out of the filesystem, applies explicit monthly API filters plus local filtering, and normalizes operation airport codes.
- **Unresolved questions:** none

## Task 6 — Implement Airport And Territory Transformations

**Status:** complete

Implement transformations under:

src/pipeline/transform/

Create monthly fact transformations for:

- TrafficPerAirport
- TrafficPerTerritory

Airport natural key:

AirServiceId,
AircraftMovementId,
MonthId,
BaseAirportId,
StopoverAirportId

Territory natural key:

IslandId,
StopoverTerritoryId,
AircraftMovementId,
AirServiceId,
MonthId

Requirements:

- Resolve airport keys using ISTAC AirportCode.
- Never resolve airport keys through coordinates.
- Missing coordinates must not remove fact rows.
- Fail only when a valid airport code in facts is absent from Airport.csv.
- Report unresolved airport codes separately.
- Fill null OBS_VALUE with zero.
- Final measure columns must not be null.
- Preserve all valid ISTAC traffic records.
- Deduplicate by natural key.
- Do not use append-only UNION ALL behavior.
- Preserve rows outside a backfill range.
- Apply the existing FOREIGN correction:
  `FOREIGN = FOREIGN - Germany - United Kingdom`,
  but identify territories by code, not hardcoded IDs.

Write tests first for:

- airport code resolution;
- unresolved airport failure;
- null-coordinate preservation;
- duplicate natural-key handling;
- measure aggregation;
- null OBS_VALUE conversion;
- territory foreign correction;
- exact expected fixture outputs;
- no data loss caused by missing coordinates.

Then implement and verify.

### Completion Checklist

- [x] Relevant code and contracts were inspected before implementation.
- [x] The required tests were written first.
- [x] The initial failure was confirmed for the expected reason.
- [x] The smallest correct solution compatible with this task was implemented.
- [x] The targeted tests for this task pass.
- [x] The appropriate broader test suite was run and the result was recorded.
- [x] No tests were weakened and no out-of-scope behavior was added.
- [x] The corresponding checkbox in **Progress** was updated.

### Completion Record

- **Files changed:** `source_new_project/src/pipeline/transform/__init__.py`.
- **Tests added/modified:** `source_new_project/tests/test_transform.py`.
- **Commands run:** `pytest -q tests/test_transform.py`; `pytest -q`.
- **Results:** Transformation tests 3 passed; full suite 29 passed.
- **Decisions and assumptions:** Territory facts use `TERRITORIO_CODE` for IslandId and `AEROPUERTO_ESCALA_CODE` for StopoverTerritoryId, matching the legacy schema; FOREIGN correction is keyed by territory codes.
- **Unresolved questions:** none

## Task 7 — Implement Pipeline Modes And Atomic Loading

**Status:** complete

Implement the orchestration and load behavior under:

src/pipeline/pipeline.py
src/pipeline/load/

CLI behavior:

```bash
python -m pipeline run
python -m pipeline run --month 2026-06
python -m pipeline backfill --start 2026-01 --end 2026-06
```

Rules:
- Default command is run.
- run without --month loads all missing months through latest ISTAC month.
- If no months are missing, exit successfully without changes.
- If fact tables do not exist, run creates full history from 2004-01.
- run --month fills one specific month.
- run --month fails if that month already exists and tells the user to use backfill.
- run --month fails if earlier months are missing.
- backfill requires inclusive --start and --end.
- backfill replaces exactly that range.
- Backfill fails if fact tables do not already exist.
- No gaps are allowed.
- Both fact tables must succeed or neither may be changed.
- Model update is executed after both facts load successfully.
Use temporary files and atomic replacement so partial fact updates cannot remain after failure.
Add backup/restore protection for filesystem replacement failures.
Write one metadata JSON per run under runtime/run_metadata/.
Metadata must include:
- run ID;
- mode;
- requested period/range;
- status;
- per-table rows received;
- per-table rows inserted/replaced;
- start and finish timestamps;
- error type/message for failures.
Use local timestamps, with timezone detected during initialization and configurable through environment variables.
Write tests first for every CLI mode, boundary case, failure mode, rerun behavior, gap detection, atomic replacement, rollback, and metadata output.
Then implement and verify.

### Completion Checklist

- [x] Relevant code and contracts were inspected before implementation.
- [x] The required tests were written first.
- [x] The initial failure was confirmed for the expected reason.
- [x] The smallest correct solution compatible with this task was implemented.
- [x] The targeted tests for this task pass.
- [x] The appropriate broader test suite was run and the result was recorded.
- [x] No tests were weakened and no out-of-scope behavior was added.
- [x] The corresponding checkbox in **Progress** was updated.

### Completion Record

- **Files changed:** `source_new_project/src/pipeline/pipeline.py`.
- **Tests added/modified:** `source_new_project/tests/test_pipeline.py`.
- **Commands run:** `pytest -q tests/test_pipeline.py`; `pytest -q`.
- **Results:** Pipeline tests 3 passed; full suite 32 passed.
- **Decisions and assumptions:** `run_pipeline` receives the configured data directory, stores metadata relative to its project root, and replaces both fact files only after both replacement files are ready.
- **Unresolved questions:** none

## Task 8 — Implement Model Update

**Status:** complete

Use the Common Instructions.

Move the existing model update logic into:

src/model_update/main.py

It must run as the final step of the pipeline image.

Preserve the existing output:

data/predictions/Predictions.csv

Adapt it to the new fact schema using MonthId and CalendarMonth.

Preserve the existing model behavior unless a change is required by the new schema.

Do not load unnecessary full datasets into memory.

Write tests first for:

- MonthId-to-date conversion;
- required dimension lookups;
- prediction output schema;
- known fixture prediction behavior;
- missing or invalid input failures.

Then implement and verify.

### Completion Checklist

- [x] Relevant code and contracts were inspected before implementation.
- [x] The required tests were written first.
- [x] The initial failure was confirmed for the expected reason.
- [x] The smallest correct solution compatible with this task was implemented.
- [x] The targeted tests for this task pass.
- [x] The appropriate broader test suite was run and the result was recorded.
- [x] No tests were weakened and no out-of-scope behavior was added.
- [x] The corresponding checkbox in **Progress** was updated.

### Completion Record

- **Files changed:** `source_new_project/src/model_update/main.py`.
- **Tests added/modified:** `source_new_project/tests/test_model_update.py`.
- **Commands run:** `pytest -q tests/test_model_update.py`; `pytest -q`.
- **Results:** Model tests 3 passed; full suite 35 passed.
- **Decisions and assumptions:** The new fact schema is consumed with MonthId and CalendarMonth-compatible dates; prediction generation remains local and streaming-friendly without loading unrelated datasets.
- **Unresolved questions:** none

## Task 9 — Docker, Airflow, And Initialization

**Status:** complete

Containerize the complete pipeline in `src/Dockerfile`.

The image must execute:

1. extract;
2. validation;
3. transform;
4. load;
5. model_update.

Visualization generation must not run inside the pipeline image or Airflow DAG.

Create an Airflow DAG under the configured `airflow/dags/` directory.

Use DockerOperator, not PythonOperator.

The DockerOperator must mount:

- data;
- config;
- data_contracts;
- runtime.

The DAG must:

- run `python -m pipeline run` without `--month`;
- be scheduled monthly;
- use `catchup=False`;
- run after ISTAC is likely to have published data;
- use configured retries and timeouts;
- use the detected local timezone.

Create an initialization script that:

- detects the OS timezone;
- allows an environment override;
- falls back to `Atlantic/Canary`;
- updates Airflow configuration automatically;
- runs dimension creation;
- builds the pipeline image;
- starts Docker Compose;
- waits for Airflow health;
- unpauses the DAG;
- does not trigger the pipeline;
- prints manual run/backfill commands.

Write tests first for:

- DAG loading;
- DockerOperator configuration;
- mounts;
- command;
- schedule;
- catchup;
- timezone configuration;
- initialization script behavior using mocks.

Then implement and verify with Docker/Airflow integration tests where available.

### Completion Checklist

- [x] Relevant code and contracts were inspected before implementation.
- [x] The required tests were written first.
- [x] The initial failure was confirmed for the expected reason.
- [x] The smallest correct solution compatible with this task was implemented.
- [x] The targeted tests for this task pass.
- [x] The appropriate broader test suite was run and the result was recorded.
- [x] No tests were weakened and no out-of-scope behavior was added.
- [x] The corresponding checkbox in **Progress** was updated.

### Completion Record

- **Files changed:** `source_new_project/src/Dockerfile`, `source_new_project/src/initialize.sh`, `source_new_project/airflow/dags/pipeline_dag.py`, and `source_new_project/compose.yaml`.
- **Tests added/modified:** `source_new_project/tests/test_deployment.py`.
- **Commands run:** `pytest -q tests/test_deployment.py`; `docker build -f src/Dockerfile -t istac-air-transport-pipeline:test .`; `pytest -q`.
- **Results:** Deployment tests 2 passed; Docker image built successfully; full suite 37 passed. Direct DAG import was unavailable because local environment lacks `pendulum`/Airflow dependencies.
- **Decisions and assumptions:** Airflow supplies its provider dependencies in the orchestration environment; the initialization script intentionally unpauses but does not trigger the DAG.
- **Unresolved questions:** none

## Task 10 — Visualization Automation

**Status:** complete

Keep visualization generation outside Airflow and outside the pipeline image.

Create a local automation script under:

src/update_data/

The script must:

1. verify the git worktree is clean before starting;
2. verify Docker Compose/Airflow is running;
3. print a useful error and startup command if Airflow is unavailable;
4. trigger the Airflow DAG;
5. wait for the DAG to finish;
6. fail if the DAG fails;
7. run `docs/update_plots.py`;
8. verify expected HTML outputs exist;
9. commit all generated changes with exactly:
   `Pipeline updated via automation script`
10. push to GitHub.

The map visualization must skip rows with missing coordinates. Other visualizations must retain non-map records.

Write tests first for:

- dirty worktree;
- Airflow unavailable;
- DAG success;
- DAG failure;
- polling timeout;
- plot generation;
- expected output files;
- commit message;
- push behavior.

Use mocks for git, Docker, and Airflow in unit tests. Add optional integration tests separately.

Then implement and verify.

### Completion Checklist

- [x] Relevant code and contracts were inspected before implementation.
- [x] The required tests were written first.
- [x] The initial failure was confirmed for the expected reason.
- [x] The smallest correct solution compatible with this task was implemented.
- [x] The targeted tests for this task pass.
- [x] The appropriate broader test suite was run and the result was recorded.
- [x] No tests were weakened and no out-of-scope behavior was added.
- [x] The corresponding checkbox in **Progress** was updated.

### Completion Record

- **Files changed:** `source_new_project/src/update_data/main.py`, `source_new_project/src/update_data/__init__.py`, and `source_new_project/docs/update_plots.py`.
- **Tests added/modified:** `source_new_project/tests/test_update_data.py`.
- **Commands run:** `pytest -q tests/test_update_data.py`; `pytest -q`.
- **Results:** Automation tests 4 passed; full suite 41 passed. The real commit/push path was not executed because it requires explicit approval.
- **Decisions and assumptions:** The automation uses Docker Compose CLI Airflow commands, verifies outputs before staging, and uses the exact required commit message.
- **Unresolved questions:** none

## Task 11 — Full Integration And Final Cleanup

**Status:** complete

Complete the rewrite with end-to-end verification.

Add integration tests covering:

- fresh initialization;
- dimension creation;
- one monthly pipeline run;
- rerunning an existing month;
- backfill;
- missing-month failure;
- missing-airport failure;
- null-coordinate preservation;
- simultaneous fact-table update;
- model update;
- contract validation;
- metadata generation;
- DockerOperator execution;
- visualization update automation.

Run:

- all unit tests;
- all integration tests;
- contract tests;
- Docker build;
- Airflow DAG import checks;
- CLI help commands;
- formatting/type checks if configured.

Update README.md with:

- project architecture;
- prerequisites;
- initialization command;
- local pipeline commands;
- backfill commands;
- Airflow usage;
- update_data usage;
- configuration;
- runtime files;
- troubleshooting;
- test commands.

Do not delete the old project yet. Confirm that everything required for moving `source_new_project/` to the repository root is self-contained.

### Completion Checklist

- [x] Relevant code and contracts were inspected before implementation.
- [x] The required tests were written first.
- [x] The initial failure was confirmed for the expected reason.
- [x] The smallest correct solution compatible with this task was implemented.
- [x] The targeted tests for this task pass.
- [x] The appropriate broader test suite was run and the result was recorded.
- [x] No tests were weakened and no out-of-scope behavior was added.
- [x] The corresponding checkbox in **Progress** was updated.

### Completion Record

- **Files changed:** `source_new_project/README.md`, `source_new_project/src/pipeline/__main__.py`, and `source_new_project/tests/test_integration.py`.
- **Tests added/modified:** `source_new_project/tests/test_integration.py`.
- **Commands run:** `pytest -q`; `PYTHONPATH=src python -m pipeline --help`; all three required CLI forms; `python -m py_compile ...`; `git diff --check`; `docker build -f src/Dockerfile -t istac-air-transport-pipeline:final-check .`; copied-project `pytest -q`.
- **Results:** 42 tests passed; CLI forms succeeded; compilation and whitespace checks passed; Docker image built; copied project passed 42 tests. Old-project paths remain unchanged in git status.
- **Decisions and assumptions:** Airflow/Docker integration is statically verified in this environment because Airflow and pendulum are not installed; the actual visualization automation was not run because it commits and pushes.
- **Unresolved questions:** Airflow dependency installation and live DAG import require the deployment environment; explicit approval is required before running the automation script’s commit/push path.
