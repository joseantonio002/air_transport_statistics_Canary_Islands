import pandas as pd
import duckdb as db
import requests
from io import StringIO
import os
from time import sleep

def get_data_from_API_call(url):
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

def pipeline_traffic_per_airport():

    pass_t = "https://datos.canarias.es/api/estadisticas/statistical-resources/v1.0/datasets/ISTAC/C00017A_000001/~latest.csv?granularity=TIME_PERIOD[M]&lang=en&representation=TIME_PERIOD[~last=1]&granularity=TIME_PERIOD[M]"
    gm_t = "https://datos.canarias.es/api/estadisticas/statistical-resources/v1.0/datasets/ISTAC/C00017A_000002/~latest.csv?granularity=TIME_PERIOD[M]&lang=en&representation=TIME_PERIOD[~last=1]&granularity=TIME_PERIOD[M]"
    op_t = "https://datos.canarias.es/api/estadisticas/statistical-resources/v1.0/datasets/ISTAC/C00017A_000003/~latest.csv?granularity=TIME_PERIOD[M]&lang=en&representation=TIME_PERIOD[~last=1]&granularity=TIME_PERIOD[M]"

    pass_arr = "https://datos.canarias.es/api/estadisticas/statistical-resources/v1.0/datasets/ISTAC/C00017A_000004/~latest.csv?granularity=TIME_PERIOD[M]&lang=en&representation=TIME_PERIOD[~last=1]&granularity=TIME_PERIOD[M]"
    gm_arr = "https://datos.canarias.es/api/estadisticas/statistical-resources/v1.0/datasets/ISTAC/C00017A_000005/~latest.csv?granularity=TIME_PERIOD[M]&lang=en&representation=TIME_PERIOD[~last=1]&granularity=TIME_PERIOD[M]"
    op_arr = "https://datos.canarias.es/api/estadisticas/statistical-resources/v1.0/datasets/ISTAC/C00017A_000006/~latest.csv?granularity=TIME_PERIOD[M]&lang=en&representation=TIME_PERIOD[~last=1]&granularity=TIME_PERIOD[M]"

    pass_depar = "https://datos.canarias.es/api/estadisticas/statistical-resources/v1.0/datasets/ISTAC/C00017A_000007/~latest.csv?granularity=TIME_PERIOD[M]&lang=en&representation=TIME_PERIOD[~last=1]&granularity=TIME_PERIOD[M]"
    gm_depar = "https://datos.canarias.es/api/estadisticas/statistical-resources/v1.0/datasets/ISTAC/C00017A_000008/~latest.csv?granularity=TIME_PERIOD[M]&lang=en&representation=TIME_PERIOD[~last=1]&granularity=TIME_PERIOD[M]"
    op_depar = "https://datos.canarias.es/api/estadisticas/statistical-resources/v1.0/datasets/ISTAC/C00017A_000009/~latest.csv?granularity=TIME_PERIOD[M]&lang=en&representation=TIME_PERIOD[~last=1]&granularity=TIME_PERIOD[M]"

    df_pass_t = get_data_from_API_call(pass_t)
    df_gm_t = get_data_from_API_call(gm_t)
    df_op_t = get_data_from_API_call(op_t)
    sleep(5) # Avoid status code 429
    df_pass_arr = get_data_from_API_call(pass_arr)
    df_gm_arr = get_data_from_API_call(gm_arr)
    df_op_arr = get_data_from_API_call(op_arr)
    sleep(5) # Avoid status code 429
    df_pass_depar = get_data_from_API_call(pass_depar)
    df_gm_depar = get_data_from_API_call(gm_depar)
    df_op_depar = get_data_from_API_call(op_depar)

    tpa = db.read_csv(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../data/TrafficPerAirport.csv")))

    max_date_local = db.sql(' \
    SELECT MAX(Month) FROM tpa \
    ').fetchone()[0]

    pass_t = pd.concat([df_pass_t, df_pass_arr, df_pass_depar])
    op_t = pd.concat([df_op_t, df_op_arr, df_op_depar])
    gm_t = pd.concat([df_gm_t, df_gm_arr, df_gm_depar])

    g_t = gm_t.loc[gm_t['MEDIDAS_CODE'] == 'MERCANCIA'].copy(deep=True)

    m_t = gm_t.loc[gm_t['MEDIDAS_CODE'] == 'CORREO'].copy(deep=True)

    op_t.rename({'AEROPUERTO_ORIGEN_DESTINO_CODE': 'AEROPUERTO_ESCALA_CODE'}, axis=1, inplace=True)

    dfs = [
        pass_t,
        op_t,
        g_t,
        m_t
    ]

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
                raise Exception(f"The ISTAC data has more than one new month. This script wasnt properly executed last month. DF: {df.loc[0, 'MEDIDAS_CODE']}")

        elif max_date_df == max_date_local:
            raise Exception(f"There is no new data, dataframe missing data: {df.loc[0, 'MEDIDAS_CODE']}")
        else:
            raise Exception(f"The local table has newer data than the data at istac, this shouldnt happen and throws an error, dataframe missing data: {df.loc[0, 'MEDIDAS_CODE']}")

    op_t.drop('MEDIDAS_CODE', axis=1, inplace=True)
    pass_t.drop('MEDIDAS_CODE', axis=1, inplace=True)
    g_t.drop('MEDIDAS_CODE', axis=1, inplace=True)
    m_t.drop('MEDIDAS_CODE', axis=1, inplace=True)

    df_f = pass_t.merge(op_t, 
                        on=['AEROPUERTO_BASE_CODE', 'AEROPUERTO_ESCALA_CODE', 'MOVIMIENTO_AERONAVE_CODE', 'SERVICIO_AEREO_CODE', 'Month'], 
                        suffixes=("", "_op"),
                        how="outer")
    df_f.drop(columns=[col for col in df_f.columns if col.endswith('op') and not col in ['OBS_VALUE_op']], inplace=True)

    df_f = df_f.merge(m_t, 
                        on=['AEROPUERTO_BASE_CODE', 'AEROPUERTO_ESCALA_CODE', 'MOVIMIENTO_AERONAVE_CODE', 'SERVICIO_AEREO_CODE', 'Month'], 
                        suffixes=("", "_m"),
                        how='outer')
    df_f.drop(columns=[col for col in df_f.columns if col.endswith('m') and not col in ['OBS_VALUE_m']], inplace=True)

    df_f = df_f.merge(g_t, 
                        on=['AEROPUERTO_BASE_CODE', 'AEROPUERTO_ESCALA_CODE', 'MOVIMIENTO_AERONAVE_CODE', 'SERVICIO_AEREO_CODE', 'Month'], 
                        suffixes=("", "_g"),
                        how='outer')
    df_f.drop(columns=[col for col in df_f.columns if col.endswith('g') and not col in ['OBS_VALUE_g']], inplace=True)

    df_f.fillna(0, inplace=True)
    df_f['OBS_VALUE'] = df_f['OBS_VALUE'].astype(int)
    df_f['OBS_VALUE_op'] = df_f['OBS_VALUE_op'].astype(int)
    df_f['OBS_VALUE_m'] = df_f['OBS_VALUE_m'].astype(int)
    df_f['OBS_VALUE_g'] = df_f['OBS_VALUE_g'].astype(int)

    airservice = pd.read_csv(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../data/AirService.csv")))
    aircraftmovement = pd.read_csv(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../data/AircraftMovement.csv")))
    airport = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../data/Airport.csv"))

    # Replace values in df_f["TERRITORIO_CODE"] with corresponding TerritoryId
    df_f["AEROPUERTO_BASE_CODE"] = df_f["AEROPUERTO_BASE_CODE"].map(dict(zip(airport["AirportCode"], airport["AirportId"])))

    # Replace values in df_f["AEROPUERTO_ESCALA_CODE"] with corresponding TerritoryId
    df_f["AEROPUERTO_ESCALA_CODE"] = df_f["AEROPUERTO_ESCALA_CODE"].map(dict(zip(airport["AirportCode"], airport["AirportId"])))
    # Delete rows where AEROPUERTO_ESCALA_CODE hasnt matched (deleted territories like Total)
    df_f.dropna(inplace=True)

    df_f["AEROPUERTO_ESCALA_CODE"] = df_f["AEROPUERTO_ESCALA_CODE"].astype(int)

    df_f["SERVICIO_AEREO_CODE"] = df_f["SERVICIO_AEREO_CODE"].map(dict(zip(airservice['AirServiceCode'], airservice['AirServiceId'])))

    df_f["MOVIMIENTO_AERONAVE_CODE"] = df_f["MOVIMIENTO_AERONAVE_CODE"].map(dict(zip(aircraftmovement['AircraftMovementCode'], aircraftmovement['AircraftMovementId'])))

    df_f.rename({
        'AEROPUERTO_BASE_CODE': 'BaseAirportId',
        'AEROPUERTO_ESCALA_CODE': 'StopoverAirportId',
        'MOVIMIENTO_AERONAVE_CODE': 'AircraftMovementId',
        'SERVICIO_AEREO_CODE': 'AirServiceId',
        'TIME_PERIOD_CODE': 'Month',
        'OBS_VALUE': 'Passengers',
        'OBS_VALUE_g': 'Goods',
        'OBS_VALUE_m': 'Mail',
        'OBS_VALUE_op': 'Operations'
    }, axis=1, inplace=True)

    df_f['BaseAirportId'] = df_f['BaseAirportId'].astype(int)

    df_f = df_f[['AirServiceId', 'AircraftMovementId', 'Month', 'BaseAirportId', 'StopoverAirportId', 'Passengers', 'Operations', 'Goods', 'Mail']]

    final = db.sql('SELECT * FROM tpa UNION ALL SELECT * FROM df_f')

    final.to_csv(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../data/TrafficPerAirport.csv")))

