# Automated Data Pipeline for Canary Islands Air Transport Statistics

This project implements an automated data pipeline that collects, processes, and visualizes air transport statistics for the Canary Islands. The pipeline retrieves new data each month, updates visual dashboards, and maintains a clean, structured dataset for analysis.

### [Web page](https://joseantonio002.github.io/air_transport_statistics_Canary_Islands/)

![img1](./air_transport_pipeline_diagram.png)

# Description

This project is an automated data pipeline that collects, processes, and visualizes air transport statistics from the Canary Islands, updating itself monthly. It was built using Python, DuckDB, Prophet, Plotly, and Apache Airflow.

### [Here I explain everything](https://joseantonio002.github.io/blog/post-4/)

# Extra

[Data source](https://www3.gobiernodecanarias.org/istac/statistical-visualizer/visualizer/collection.html?resourceType=collection&agencyId=ISTAC&resourceId=C00017A_000001)

[Airport Data](https://ourairports.com/data/?spm=a2ty_o01.29997173.0.0.59a6c921d0cVCU)

Python version used for the project == 3.12.11

## Docker And Airflow

Initialize the project after cloning it:

```bash
./src/initialize.sh
```

The initializer detects the Airflow user ID and Docker socket group ID, then
stores machine-specific Compose settings in `src/runtime/compose.env`. Optional
Airflow settings remain in `src/.env`.

Use both environment files for later Compose lifecycle commands:

```bash
docker compose --env-file src/.env --env-file src/runtime/compose.env -f src/compose.yaml stop
docker compose --env-file src/.env --env-file src/runtime/compose.env -f src/compose.yaml start
docker compose --env-file src/.env --env-file src/runtime/compose.env -f src/compose.yaml down
docker compose --env-file src/.env --env-file src/runtime/compose.env -f src/compose.yaml up -d
```

`docker compose down` preserves the PostgreSQL named volume. Using `down -v`
also deletes that volume.
