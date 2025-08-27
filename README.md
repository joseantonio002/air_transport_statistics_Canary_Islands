[Data source](https://www3.gobiernodecanarias.org/istac/statistical-visualizer/visualizer/collection.html?resourceType=collection&agencyId=ISTAC&resourceId=C00017A_000001)

Plan for now:

Upload to DuckDB two tables, one for the data grouped by territory and airport, and another for the data grouped by origin airport and destination airport

Table: TrafficPerTerritory
+----------------------+----------+
| Column Name          | Type     |
+----------------------+----------+
| IslandId             | UTINYINT |
| LayoverAirportId     | UTINYINT |
| AircraftMovementId   | UTINYINT |
| AirServiceId         | UTINYINT |
| Date                 | DATE     |
| Passengers           | UINTEGER |
| Goods                | UINTEGER |
| Mail                 | UINTEGER |
| Operations           | UINTEGER |
+----------------------+----------+
Remove "Total" values (or not... think about this), dates with only the year, "Canarias" from Territory (is the sum of all territories), "Comercial" from AircraftMovement (its the sum of regular + non regular)

Table: Island
+----------------------+----------+
| Column Name          | Type     |
+----------------------+----------+
| TerritoryId          | UTINYINT |
| Territory            | VARCHAR  |
+----------------------+----------+

Table: LayoverAirport
+----------------------+----------+
| Column Name          | Type     |
+----------------------+----------+
| LayoverAirportId     | UTINYINT |
| LayoverAirport       | VARCHAR  |
+----------------------+----------+

Table: AircraftMovement
+----------------------+----------+
| Column Name          | Type     |
+----------------------+----------+
| AircraftMovementId   | UTINYINT |
| AircraftMovement     | VARCHAR  |
+----------------------+----------+

Table: AirService
+----------------------+----------+
| Column Name          | Type     |
+----------------------+----------+
| AirServiceId         | UTINYINT |
| AirService           | VARCHAR  |
+----------------------+----------+

Table: TrafficPerAirport
+----------------------+----------+
| Column Name          | Type     |
+----------------------+----------+
| BaseAirportId        | UTINYINT |
| LayoverAirportId     | UTINYINT |
| AircraftMovementId   | UTINYINT |
| AirServiceId         | UTINYINT |
| Date                 | DATE     |
| Passengers           | UINTEGER |
| Goods                | UINTEGER |
| Mail                 | UINTEGER |
| Operations           | UINTEGER |
+----------------------+----------+

Table: TrafficPerAirport
+----------------------+----------+
| Column Name          | Type     |
+----------------------+----------+
| TrafficPerAirportId  | UTINYINT |
| TrafficPerAirport    | VARCHAR  |
+----------------------+----------+

Maybe to make it less rows, rows with null aka 0 delete them
