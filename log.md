In this file I will be documenting what I do every day

## 26/08/25 - 27/08/25

- Start the project
- Choose the data
- Analyze the data
- Think of an execution plan
1) Data modeling
2) Pipeline into datalake
3) Install and understand duckdb
4) Analytical queries
5) Plan visualization
6) Train models
7) Visualization
8) Orchestration
9) Deployment

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

## 30/08/25

Current step: 2) Pipeline into warehouse

Finish creating dimensions tables

To create the pipeline into the warehouse, first create and load the two facts tables with all the data until now, and once we have it
we can then do the pipeline only querying the last data from the API. All the code that creates tables that will not be modified in the pipeline will be stored in the "code_not_pipeline_tables" folder. Pipeline code will be stored in the "code_pipeline"

I think TrafficPerTerritory is already done but I have to check, tomorrow

## 31/08/25

Current step: 2) Pipeline into warehouse, creating the two facts tables before the final pipeline

TrafficPerTerritory had an error as I suspected, I was deleting nan values before filling with 0 the observed values with nan. Thats why the number of rows wasnt the one expected. Finished TrafficPerTerritory

TrafficPerAirport:
There is something wrong with the operations or passenger data, passenger data has double the rows that operations when they should have the same
Check tomorrow

## 1/09/25

Current step: 2) Pipeline into warehouse, creating the two facts tables before the final pipeline
After checking, the operations dataset does not have all the airports that the passenger dataset has, so well do a full outer join, fill nan with 0 

Finished the difficult part about creating TrafficPerAirport, only thing left is to change names to Id and rename columns, tomorrow

## 2/09/25

Finished tables

## 3/09/25

Current step: 2) Pipeline into warehouse, creating the two facts tables before the final pipeline

Now that I have the tables ready to upload, I will install duckdb, upload them and then start the pipeline scripts.\
Okay so after some investigation, we dont really need to upload the csv to tables, we can work with them as they are,
in the next SQL project I do I will create tables, functions, views and all of that... In this project creating the table
is not necessary we can run the queries over the csv file no problem.

In other words, instead of storing the data in tables for now reason when we already have the csv files and we dont need any additional features from the database (only thing we need is retrieve the data for analytical purpouses and we can do that with csv files), following a **data lake** approach

So the plan is:
1) End steps 2) and 3) 
2) Start step 4) Analytical Queries

## 4/09/25

The standard DuckDB Python API provides a SQL interface compliant with the DB-API 2.0 
specification described by PEP 249 similar to the SQLite Python API
https://peps.python.org/pep-0249/
Check that

Possible improvements:
Add algorithm to retrieve missing data for more than one month automatically
Refactorize pipeline codes (they are very similar)

Finished pipeline scripts

Now do some analytical queries with duckdb just for the fun of it and that I could show on the dashboard

## 5/09/25

Doing analytical queries

## 6/09/25

Continue analytical queries

## 7/09/25

end queries

Start:\
5) Plan visualization
6) Train models

First plan the visualization so we choose some metrics to predict, and then train the models to do so

## 8/09/25

Current step:\
5) Plan visualization
6) Train models

Make four visualizations:\
1) Map visualization with tpt data and filters for all variables
2) Line graph with tpa data and filters for all variables
3) Line graph with tpt data AND predictions for passenger arrivals, filter each island 
4) Top foreign airports for each measure

The idea of the models is that they would be retrained every time there is new data, so their training is part of the data pipeline

## 9/09/25

Current step:\
6) Train models

For tomorrow, do prophet with all islands not just one and pipeline style

JUST REALIZED THERE IS A BUG IN THE CREATION OF THE TABLES, okay easy to spot, basically because stopoverterritory FOREIGN counts GB, Germany and the rest of the world, when we group and sum is adding GB and Germany twice. To solve this, when we create TrafficPerTerritory, make sure that FOREIGN is FOREIGN = - GB - Germnay

## 13/09/25

Current step:\
6) Train models

Lets simplify the visualization and for the predictions only passengers

## 16/09/25

Current step:\
7) Visualization

## 17/09/25

Current step:\
7) Visualization

## 18/09/25

Current step:\
7) Visualization

Upload bigger files to git & github
https://git-lfs.com/

You can install git-lfs on WSL through your linux distribution's package manager. For example, in Debian or Ubuntu on WSL you would type:

sudo apt-get install git-lfs
git lfs install

Okay, problem, so I cant push the visualization because the html is too large, so I use lfs to push it, but if I use lfs on html files then they dont work with github pages. 

So basically dont use lfs and reduce the amount of data so I can push it withouth lfs. Only options If I dont want to use paid hosts

Deployment in docs, next day finish the remaining plots

## 20/09/25

Due to the size limitation, we can not make a line graph between each airport for all the months and filters for air service and aircraft movement\
Since the purpouse of this visualization is see the data between airports in the maximum time possible, lets remove air service and aircraf movement and just use the totals, and lets see if this way the file size is not too big

Another visualization done

## 21/09/25

Finished visualizations. We can start with the final step, orchestration

## 28/09/2025

Because the airflow dag is a python script, you need to import the functions used in the dag or write them in the same dag script.\
The problem is that you cant import a function from a ipynb. So I have to write all the code in python scripts. So basically have a last look at the\
code, make sure everything is correct and then create the scripts so I can import the code in the dags

## 30/09/2025

Fix the relative paths in the pipeline codes so it can be executed from anywhere

## 01/10/2025

Scripts ready

Now I have to install airflow, create the dag and thats it
Tomorrow check if the dag runs 

## 02/10/2025

I give up with airflow, i cant get it to work and I want to finish this project already so I can move on. I'll do a simple cron job.
For tomorrow delete all related to airflow and create the cron job