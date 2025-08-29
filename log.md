In this file I will be documenting what I do every day

## 26/08/25 - 27/08/25

- Start the project
- Choose the data
- Analyze the data
- Think of an execution plan
1) Data modeling
2) Pipeline into warehouse (duckdb)
3) Install and understand duckdb
4) Analytical queries
5) Train models
6) Visualization
7) Orchestration
8) Deployment

Upload to DuckDB two tables:
- One for the data grouped by territory and airport
- Another for the data grouped by origin airport and destination airport

First I need to know what data am I gonna store

## 28/08/25

Current step: 1) Data modeling

Idea: Do a prototype for the map visualization, that way I know if its worth it storing the information about airports and I know 

Steps of the prototype:\

1) Get TrafficPerAirport mock data (First find a way to create Airport table with latitude and longitude, then TrafficPerAirport)
2) Do the visualization
3) See if I can host it in github pages

Conclusion of the prototype: Yes, I can host it in github pages and it looks cool

Now That I did the prototype and I know what data I need, I can finally end the first step and start with the second step, creating the pipeline that will ingest, transform and serve the data to our data warehouse

## 29/08/25

Current step: 2) Pipeline into warehouse

First create the dimensions tables, we asume that this tables are not going to change so we only have to create them once

Airport created.

