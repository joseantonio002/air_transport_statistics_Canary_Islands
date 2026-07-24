### New Data Model

#### Facts Table: TrafficPerTerritory

| Column Name         | Type    |
| ------------------- | ------- |
| IslandId            | INTEGER |
| StopoverTerritoryId | INTEGER |
| AircraftMovementId  | INTEGER |
| AirServiceId        | INTEGER |
| MonthId             | INTEGER |
| Passengers          | BIGINT  |
| Goods               | BIGINT  |
| Mail                | BIGINT  |
| Operations          | BIGINT  |

#### Facts Table: TrafficPerAirport

| Column Name        | Type    |
| ------------------ | ------- |
| BaseAirportId      | INTEGER |
| StopoverAirportId  | INTEGER |
| AircraftMovementId | INTEGER |
| AirServiceId       | INTEGER |
| MonthId            | INTEGER |
| Passengers         | BIGINT  |
| Goods              | BIGINT  |
| Mail               | BIGINT  |
| Operations         | BIGINT  |

#### Dimension Table: CalendarMonth

| Column Name    | Type        |
| -------------- | ----------- |
| MonthId        | INTEGER     |
| MonthStartDate | DATE        |
| MonthNumber    | INTEGER     |
| MonthName      | VARCHAR(20) |
| QuarterNumber  | INTEGER     |
| QuarterName    | VARCHAR(10) |
| Year           | INTEGER     |
| YearMonth      | VARCHAR(7)  |

#### Dimension Table: Territory

| Column Name | Type         |
| ----------- | ------------ |
| TerritoryId | INTEGER      |
| Territory   | VARCHAR(255) |

#### Dimension Table: AircraftMovement

| Column Name        | Type         |
| ------------------ | ------------ |
| AircraftMovementId | INTEGER      |
| AircraftMovement   | VARCHAR(255) |

#### Dimension Table: AirService

| Column Name  | Type         |
| ------------ | ------------ |
| AirServiceId | INTEGER      |
| AirService   | VARCHAR(255) |

#### Dimension Table: Airport

| Column Name | Type         |
| ----------- | ------------ |
| AirportId   | INTEGER      |
| AirportName | VARCHAR(255) |
| Latitude    | DECIMAL(9,6) |
| Longitude   | DECIMAL(9,6) |
| CountryCode | VARCHAR(3)   |
| CountryName | VARCHAR(255) |