# Automated Data Pipeline for Canary Islands Air Transport Statistics

This project implements an automated data pipeline that collects, processes, and visualizes air transport statistics for the Canary Islands. The pipeline retrieves new data each month, updates visual dashboards, and maintains a clean, structured dataset for analysis.

### [Web page](https://joseantonio002.github.io/air_transport_statistics_Canary_Islands/)

![img1](./air_transport_pipeline_diagram.png)

# Description

Pequeña descripción de lo que he hecho, para mas info checkea mi blog



# Data modeling:

## Facts Table: TrafficPerTerritory

| Column Name           | Type       |
|-----------------------|------------|
| IslandId              | UTINYINT   |
| StopoverTerritoryId   | UTINYINT   |
| AircraftMovementId    | UTINYINT   |
| AirServiceId          | UTINYINT   |
| Month                 | DATE       |
| Passengers            | UINTEGER   |
| Goods                 | UINTEGER   |
| Mail                  | UINTEGER   |
| Operations            | UINTEGER   |

## Facts Table: TrafficPerAirport

| Column Name           | Type       |
|-----------------------|------------|
| BaseAirportId         | UINTEGER   |
| StopoverAirportId     | UINTEGER   |
| AircraftMovementId    | UTINYINT   |
| AirServiceId          | UTINYINT   |
| Month                 | DATE       |
| Passengers            | UINTEGER   |
| Goods                 | UINTEGER   |
| Mail                  | UINTEGER   |
| Operations            | UINTEGER   |

## Dimenson Table: Territory

| Column Name   | Type      |
|---------------|-----------|
| TerritoryId   | UTINYINT  |
| Territory     | VARCHAR   |

## Dimension Table: AircraftMovement

| Column Name            | Type      |
|------------------------|-----------|
| AircraftMovementId     | UTINYINT  |
| AircraftMovement       | VARCHAR   |

## Dimension Table: AirService

| Column Name    | Type      |
|----------------|-----------|
| AirServiceId   | UTINYINT  |
| AirService     | VARCHAR   |

## Dimension Table: Airport

| Column Name          | Type      |
|----------------------|-----------|
| AirportId            | UINTEGER  |
| AirportName          | VARCHAR   |
| Latitude             | DOUBLE    |
| Longitude            | DOUBLE    |
| CountryCode          | VARCHAR   |
| CountryName          | VARCHAR   |

# Extra

[Data source](https://www3.gobiernodecanarias.org/istac/statistical-visualizer/visualizer/collection.html?resourceType=collection&agencyId=ISTAC&resourceId=C00017A_000001)

[Airport Data](https://ourairports.com/data/?spm=a2ty_o01.29997173.0.0.59a6c921d0cVCU)

Python version used for the project == 3.12.11