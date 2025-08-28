[Data source](https://www3.gobiernodecanarias.org/istac/statistical-visualizer/visualizer/collection.html?resourceType=collection&agencyId=ISTAC&resourceId=C00017A_000001)

pro-tip vscode: to visualize the readme ctrl+shift+v

# Plan for now

Upload to DuckDB two tables:
- One for the data grouped by territory and airport
- Another for the data grouped by origin airport and destination airport

First I need to know what data am I gonna store

For the second table, Im gonna do a prototype of the visualization to see 
if its worth it storing information about airport latitude and longitude

## Table: TrafficPerTerritory

| Column Name           | Type       |
|-----------------------|------------|
| IslandId              | UTINYINT   |
| LayoverTerritoryId    | UTINYINT   |
| AircraftMovementId    | UTINYINT   |
| AirServiceId          | UTINYINT   |
| Date                  | DATE       |
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
 'España' 'Total' 'Alemania' 'Lanzarote' 'Fuerteventura' 'Gran Canaria' 'Tenerife'
 'La Gomera' 'La Palma' 'El Hierro']

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
| LayoverAirportId      | UINTEGER   |
| AircraftMovementId    | UTINYINT   |
| AirServiceId          | UTINYINT   |
| Date                  | DATE       |
| Passengers            | UINTEGER   |
| Goods                 | UINTEGER   |
| Mail                  | UINTEGER   |
| Operations            | UINTEGER   |

## Table: Airport

| Column Name          | Type      |
|----------------------|-----------|
| AirportId            | UINTEGER  |
| AirportName          | VARCHAR   |
| Latitude
| Longitude
| Country

