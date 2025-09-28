# %%
import pandas as pd
import duckdb as db
import requests
from io import StringIO

# %%
def get_data_from_API_call_tpt(url):
    """
    Send a GET request to the specified URL and return the response
    content as a file-like StringIO object.

    Parameters
    ----------
    url : str
        The complete endpoint URL from which data will be fetched.

    Returns
    -------
    io.StringIO
        A file-like object containing the UTF-8 decoded response text.

    Raises
    ------
    Exception
        If the HTTP status code is anything other than 200, an
        exception is raised with a message that includes the received
        status code.
    """
    # Send HTTP GET request
    response = requests.get(url)
    # Check if the request was successful
    if response.status_code == 200:
        data = StringIO(response.content.decode("utf-8"))
        return pd.read_csv(data)
    else:
        print("Failed to retrieve data. Status code:", response.status_code)    
        raise Exception(f"Failed to retrieve data. Status code: {response.status_code}")

def pipeline_traffic_per_territory():
    # %%
    # url passenger data
    url_pas = "https://datos.canarias.es/api/estadisticas/statistical-resources/v1.0/datasets/ISTAC/C00017A_000013/~latest.csv?lang=en&representation=TIME_PERIOD[~last=1]&granularity=TIME_PERIOD[M]"
    # url goods and mail data
    url_gm = "https://datos.canarias.es/api/estadisticas/statistical-resources/v1.0/datasets/ISTAC/C00017A_000014/~latest.csv?lang=en&representation=TIME_PERIOD[~last=1]&granularity=TIME_PERIOD[M]"
    # url operations
    url_o = "https://datos.canarias.es/api/estadisticas/statistical-resources/v1.0/datasets/ISTAC/C00017A_000015/~latest.csv?lang=en&representation=TIME_PERIOD[~last=1]&granularity=TIME_PERIOD[M]"

    # %%
    pas = get_data_from_API_call_tpt(url_pas)
    gm = get_data_from_API_call_tpt(url_gm)
    op = get_data_from_API_call_tpt(url_o)

    # %%
    # For some reason the operations table changes the name of the column of the stopover airport
    op.rename({'AEROPUERTO_ORIGEN_DESTINO_CODE': 'AEROPUERTO_ESCALA_CODE', 'AEROPUERTO_ORIGEN_DESTINO#en': 'AEROPUERTO_ESCALA#en'}, axis=1, inplace=True)

    # %%
    dfs = [pas, gm, op]

    # %%
    tpt = db.read_csv("../../../data/TrafficPerTerritory.csv")

    # %%
    max_date_local = db.sql(' \
    SELECT MAX(Month) FROM tpt \
    ').fetchone()[0]

    # %%
    for df in dfs:
        df['Month'] = pd.to_datetime(df['TIME_PERIOD#en'], format="%m/%Y").dt.date
        df.drop(columns=df.columns[df.columns.str.endswith("#es") | df.columns.str.endswith("#en")], inplace=True)
        df.drop(columns=['ESTADO_OBSERVACION_CODE', 'TIME_PERIOD_CODE'], inplace=True)
        df['OBS_VALUE'] = df['OBS_VALUE'].fillna(0).astype(int)

        max_date_df = db.sql(' \
            SELECT MAX(Month) FROM df \
            ').fetchone()[0]
        
        month_diff = (max_date_df.year - max_date_local.year) * 12 + (max_date_df.month - max_date_local.month)

        if max_date_df > max_date_local:
            print("There is new data")
            # If the difference is more than one month, then you skipped a month, shouldnt happen but we make the error just in case
            if month_diff > 1:
                # Possible improvements: make an algorithm that retrieves the missing data automatically
                raise Exception(msg=f"The ISTAC data has more than one new month. This script wasnt properly executed last month. DF: {df.loc[0, 'MEDIDAS_CODE']}")

        elif max_date_df == max_date_local:
            raise Exception(msg=f"There is no new data, dataframe missing data: {df.loc[0, 'MEDIDAS_CODE']}")
        else:
            raise Exception(f"The local table has newer data than the data at istac, this shouldnt happen and throws an error, dataframe missing data: {df.loc[0, 'MEDIDAS_CODE']}")

    print("No error thrown, we can continue the execution")

    # %%
    pas.drop('MEDIDAS_CODE', axis=1, inplace=True)
    op.drop('MEDIDAS_CODE', axis=1, inplace=True)

    # %%
    df_f = pas.merge(op, how='outer',
                    on=['MOVIMIENTO_AERONAVE_CODE', 'AEROPUERTO_ESCALA_CODE', 'TERRITORIO_CODE', 'SERVICIO_AEREO_CODE', 'Month'],
                    suffixes=(None, "_op"))

    # %%
    only_goods = gm.loc[gm['MEDIDAS_CODE'] == "MERCANCIA"].copy(deep=True)
    only_mail = gm.loc[gm['MEDIDAS_CODE'] == "CORREO"].copy(deep=True)

    only_goods.drop('MEDIDAS_CODE', axis=1, inplace=True)
    only_mail.drop('MEDIDAS_CODE', axis=1, inplace=True)

    # %%
    # Merge p&op with goods 
    df_f = df_f.merge(only_goods, 
                    on=['TERRITORIO_CODE', 'AEROPUERTO_ESCALA_CODE', 'MOVIMIENTO_AERONAVE_CODE', 'SERVICIO_AEREO_CODE', 'Month'], 
                    suffixes=("", "_goods"))

    df_f.drop(columns=[col for col in df_f.columns if col.endswith('goods') and col not in ['OBS_VALUE_goods']], inplace=True)

    # Merge p&op&goods with mail 
    df_f = df_f.merge(only_mail, 
                    on=['TERRITORIO_CODE', 'AEROPUERTO_ESCALA_CODE', 'MOVIMIENTO_AERONAVE_CODE', 'SERVICIO_AEREO_CODE', 'Month'], 
                    suffixes=("", "_mail"))

    df_f.drop(columns=[col for col in df_f.columns if col.endswith('mail') and col not in ['OBS_VALUE_mail']], inplace=True)

    # %%
    territory = pd.read_csv('../../../data/Territory.csv')
    airservice = pd.read_csv('../../../data/AirService.csv')
    aircraftmovement = pd.read_csv('../../../data/AircraftMovement.csv')

    # %%
    # Replace values in df_f["TERRITORIO_CODE"] with corresponding TerritoryId
    df_f["TERRITORIO_CODE"] = df_f["TERRITORIO_CODE"].map(dict(zip(territory["TerritoryCode"], territory["TerritoryId"])))

    # Replace values in df_f["AEROPUERTO_ESCALA_CODE"] with corresponding TerritoryId
    df_f["AEROPUERTO_ESCALA_CODE"] = df_f["AEROPUERTO_ESCALA_CODE"].map(dict(zip(territory["TerritoryCode"], territory["TerritoryId"])))
    # Delete rows where AEROPUERTO_ESCALA_CODE hasnt matched (deleted territories like Total)
    df_f.dropna(inplace=True)
    df_f["AEROPUERTO_ESCALA_CODE"] = df_f["AEROPUERTO_ESCALA_CODE"].astype(int)

    df_f["SERVICIO_AEREO_CODE"] = df_f["SERVICIO_AEREO_CODE"].map(dict(zip(airservice['AirServiceCode'], airservice['AirServiceId'])))

    df_f["MOVIMIENTO_AERONAVE_CODE"] = df_f["MOVIMIENTO_AERONAVE_CODE"].map(dict(zip(aircraftmovement['AircraftMovementCode'], aircraftmovement['AircraftMovementId'])))

    # %%
    df_f.rename({
    'TERRITORIO_CODE': 'IslandId',
    'AEROPUERTO_ESCALA_CODE': 'StopoverTerritoryId',
    'MOVIMIENTO_AERONAVE_CODE': 'AircraftMovementId',
    'SERVICIO_AEREO_CODE': 'AirServiceId',
    'TIME_PERIOD#en': 'Month',
    'OBS_VALUE': 'Passengers',
    'OBS_VALUE_op': 'Operations',
    'OBS_VALUE_goods': 'Goods',
    'OBS_VALUE_mail': 'Mail'
    }, inplace=True, axis=1)

    # %%
    df_f = df_f[['IslandId', 'StopoverTerritoryId', 'AircraftMovementId', 'AirServiceId', 'Month', 'Passengers', 'Operations', 'Goods', 'Mail']]

    # %% [markdown]
    # Delete Germany and Uk passengers from FOREIGN passengers

    # %%
    # Make a copy to work with
    df_copy = df_f.copy()

    # Get all rows where StopoverTerritoryId == 9 (FOREIGN)
    foreign_mask = df_f['StopoverTerritoryId'] == 9
    foreign_rows = df_f[foreign_mask].copy()

    # Define the measure columns to subtract from
    measure_cols = ['Passengers', 'Operations', 'Goods', 'Mail']

    # For each foreign row, find and subtract corresponding GERMANY (14) and UK (8) rows
    for idx in foreign_rows.index:
        # Get the identifying values for this row
        island_id = df_f.loc[idx, 'IslandId']
        aircraft_id = df_f.loc[idx, 'AircraftMovementId']
        airservice_id = df_f.loc[idx, 'AirServiceId']
        month = df_f.loc[idx, 'Month']
        
        # Find corresponding GERMANY row (StopoverTerritoryId == 14)
        germany_mask = (
            (df_f['IslandId'] == island_id) &
            (df_f['AircraftMovementId'] == aircraft_id) &
            (df_f['AirServiceId'] == airservice_id) &
            (df_f['Month'] == month) &
            (df_f['StopoverTerritoryId'] == 14)
        )
        
        # Find corresponding UK row (StopoverTerritoryId == 8)
        uk_mask = (
            (df_f['IslandId'] == island_id) &
            (df_f['AircraftMovementId'] == aircraft_id) &
            (df_f['AirServiceId'] == airservice_id) &
            (df_f['Month'] == month) &
            (df_f['StopoverTerritoryId'] == 8)
        )
        
        # Initialize subtraction values
        subtract_values = {col: 0 for col in measure_cols}
        
        # Add values from GERMANY row if it exists
        if germany_mask.any():
            germany_idx = df_f[germany_mask].index[0]
            for col in measure_cols:
                subtract_values[col] += df_f.loc[germany_idx, col]
        
        # Add values from UK row if it exists
        if uk_mask.any():
            uk_idx = df_f[uk_mask].index[0]
            for col in measure_cols:
                subtract_values[col] += df_f.loc[uk_idx, col]
        
        # Subtract from the FOREIGN row
        for col in measure_cols:
            df_copy.loc[idx, col] = df_f.loc[idx, col] - subtract_values[col]

    # Update the original dataframe
    df_f.update(df_copy)

    # %%
    final = db.sql('SELECT * FROM tpt UNION ALL SELECT * FROM df_f')

    # %%
    final.to_csv('../../../data/TrafficPerTerritory.csv')


