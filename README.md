[Data source](https://www3.gobiernodecanarias.org/istac/statistical-visualizer/visualizer/collection.html?resourceType=collection&agencyId=ISTAC&resourceId=C00017A_000001)
[Airport Data](https://ourairports.com/data/?spm=a2ty_o01.29997173.0.0.59a6c921d0cVCU)

Python version used for the project == 3.12.11

# Data modeling:

## Table: TrafficPerTerritory

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

## Table: Territory

| Column Name   | Type      |
|---------------|-----------|
| TerritoryId   | UTINYINT  |
| Territory     | VARCHAR   |

Values: ['Reino Unido' 'Extranjero' 'Canarias' 'España (excluida Canarias)'
  'Alemania' 'Lanzarote' 'Fuerteventura' 'Gran Canaria' 'Tenerife'
 'La Gomera' 'La Palma' 'El Hierro' 'Total']

## Table: AircraftMovement

| Column Name            | Type      |
|------------------------|-----------|
| AircraftMovementId     | UTINYINT  |
| AircraftMovement       | VARCHAR   |

Values: ['Arrival' 'Departure' 'Total']

## Table: AirService

| Column Name    | Type      |
|----------------|-----------|
| AirServiceId   | UTINYINT  |
| AirService     | VARCHAR   |

Values: ['Comercial (Total)' 'Other comercial services' 'No regular' 'Regular']

## Table: TrafficPerAirport

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

## Table: Airport


| Column Name          | Type      |
|----------------------|-----------|
| AirportId            | UINTEGER  |
| AirportName          | VARCHAR   |
| Latitude             | DOUBLE    |
| Longitude            | DOUBLE    |
| CountryCode          | VARCHAR   |
| CountryName          | VARCHAR   |