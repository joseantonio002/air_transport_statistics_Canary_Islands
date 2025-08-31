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

pro-tip vscode: to visualize the readme ctrl+shift+v

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

## 29/08/25

Current step: 2) Pipeline into warehouse

Finish creating dimensions tables

To create the pipeline into the warehouse, first create and load the two facts tables with all the data until now, and once we have it
we can then do the pipeline only querying the last data from the API. All the code that creates tables that will not be modified in the pipeline will be stored in the "code_not_pipeline_tables" folder. Pipeline code will be stored in the "code_pipeline"

I think TrafficPerTerritory is already done but I have to check, tomorrow

## 30/08/25

Current step: 2) Pipeline into warehouse, creating the two facts tables before the final pipeline

TrafficPerTerritory had an error as I suspected, I was deleting nan values before filling with 0 the observed values with nan. Thats why the number of rows wasnt the one expected. Finished TrafficPerTerritory

TrafficPerAirport:
There is something wrong with the operations or passenger data, passenger data has double the rows that operations when they should have the same
Check tomorrow

