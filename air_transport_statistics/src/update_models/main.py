import pandas as pd
import duckdb as db
from prophet import Prophet
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from load_config.config import load_config

def pipeline_models():
    config = load_config(PROJECT_ROOT)
    data_dir = config.paths.data

    df = pd.read_csv(data_dir / "TrafficPerTerritory.csv")
    calendar_month = pd.read_csv(
        data_dir / "CalendarMonth.csv",
        usecols=["MonthId", "MonthStartDate"],
    )
    df = df.merge(calendar_month, on="MonthId", how="left", validate="many_to_one")
    if df["MonthStartDate"].isna().any():
        raise ValueError("TrafficPerTerritory contains MonthId values missing from CalendarMonth")
    df.rename({"MonthStartDate": "Month"}, axis=1, inplace=True)
    df["Month"] = pd.to_datetime(df["Month"], format="%Y-%m-%d")

    islands_id = [0, 1, 2, 3, 4, 5, 6, 7]
    observed_values = ["Passengers"]
    predictions_for_each_island = []

    for island_id in islands_id:
        for observed_value in observed_values:
            df_prophet = df.loc[(df['AirServiceId'] == 0) & (df['AircraftMovementId'] == 2) & 
                                    (df['IslandId'] == island_id)].copy(deep=True)
            df_prophet = df_prophet.groupby('Month').sum()[[observed_value]].copy(deep=True)
            df_prophet.reset_index(inplace=True)
            df_prophet.rename({'Month': 'ds', observed_value: 'y'}, axis=1, inplace=True)
            df_prophet.loc[(df_prophet['ds'] >= '2020-03-01') & (df_prophet['ds'] < '2022-06-01'), 'y'] = None
            m = Prophet()
            m.fit(df_prophet)
            future = m.make_future_dataframe(periods=12, freq='MS') 
            predictions_for_each_island.append((island_id, m.predict(future)[['ds', 'yhat_lower', 'yhat', 'yhat_upper']], observed_value, df_prophet))

    final = predictions_for_each_island[0][1].copy()
    final['IslandId'] = predictions_for_each_island[0][0]

    for pr in predictions_for_each_island[1:]:
        pr[1]['IslandId'] = pr[0]
        final = pd.concat([final, pr[1]], ignore_index=True)

    ter = pd.read_csv(data_dir / "Territory.csv")
    db.register("tpt", df)
    db.register("ter", ter)
    db.register("final", final)

    final = db.sql(f"SELECT TerritoryName AS Island, ds AS Month, RealPassengers, yhat_lower, yhat, yhat_upper \
            FROM (SELECT IslandId, Month, SUM(Passengers) AS RealPassengers \
                    FROM tpt WHERE AirServiceId = 0 AND AircraftMovementId = 2 \
                            GROUP BY IslandId, Month ORDER BY IslandId, Month) t \
            RIGHT JOIN final f ON t.IslandId = f.IslandId AND t.Month = f.ds INNER JOIN ter ON ter.TerritoryId = f.IslandId \
            ORDER BY 1,2").df()

    predictions_dir = data_dir / "predictions"
    predictions_dir.mkdir(parents=True, exist_ok=True)
    final.to_csv(predictions_dir / "Predictions.csv", index=False)

if __name__ == "__main__":
    pipeline_models()
