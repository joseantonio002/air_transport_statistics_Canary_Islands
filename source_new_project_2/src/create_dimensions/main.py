import pandas as pd
import requests
from io import StringIO
from calendar import month_name
from datetime import date

def _get_data_from_API_call(url: str):
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
        return data
    else:
        print("Failed to retrieve data. Status code:", response.status_code)    
        raise Exception(f"Failed to retrieve data. Status code: {response.status_code}")

# https://www3.gobiernodecanarias.org/istac/statistical-visualizer/visualizer/data.html?resourceType=dataset&agencyId=ISTAC&resourceId=C00017A_000001&version=%7Elatest&multidatasetId=ISTAC%3AC00017A_000001#visualization/table
LATEST_DATA_AIRPORTS = "https://datos.canarias.es/api/estadisticas/statistical-resources/v1.0/datasets/ISTAC/C00017A_000001/~latest.csv?lang=en"
# https://www3.gobiernodecanarias.org/istac/statistical-visualizer/visualizer/data.html?resourceType=dataset&agencyId=ISTAC&resourceId=C00017A_000013&version=%7Elatest&multidatasetId=ISTAC%3AC00017A_000004#visualization/table
LATEST_DATA_REMANING_TABLES = "https://datos.canarias.es/api/estadisticas/statistical-resources/v1.0/datasets/ISTAC/C00017A_000013/~latest.csv?lang=en"
# Airport code column in ourairports dataset
JOIN_COL_OUR_AIRPORT = 'ident' 

def create_airports():
  df: pd.DataFrame = pd.read_csv(_get_data_from_API_call(LATEST_DATA_AIRPORTS))
  df.drop(columns=df.columns[df.columns.str.endswith('#es')], inplace=True)

  # Dataframe with every country that appears in the original dataset and its iso code
  countries: pd.DataFrame = df.loc[df['AEROPUERTO_ESCALA_CODE'].str.match(r'^[A-Z]{2}$', na=False), ['AEROPUERTO_ESCALA#en', 'AEROPUERTO_ESCALA_CODE']]
  countries.drop_duplicates(inplace=True)
  countries.rename({'AEROPUERTO_ESCALA#en': 'CountryName', 'AEROPUERTO_ESCALA_CODE': 'iso_country'}, inplace=True, axis=1)

  # Delete aggregate and unnecessary rows
  # Rest of/Remain of AEROPUERTO_ESCALA#en have "_O" at the end of their code
  df_f: pd.DataFrame = df.loc[~df['AEROPUERTO_ESCALA_CODE'].str.endswith('_O')]
  # Delete entries with the whole country
  df_f = df_f.loc[~df_f['AEROPUERTO_ESCALA_CODE'].str.match(r'^[A-Z]{2}$', na=False)]
  # Delete autonomous communities (Their code is like ES[0-9][0-9]) 
  df_f = df_f.loc[~df_f['AEROPUERTO_ESCALA_CODE'].str.match(r'^ES[0-9]{2}$', na=False)]
  # Delete sum of entire island
  df_f = df_f.loc[~df_f['AEROPUERTO_ESCALA_CODE'].str.match(r'^ES70[0-9]$', na=False)]
  # Delete sum of all autonomous communities and sum of all islands
  df_f = df_f.loc[~((df_f['AEROPUERTO_ESCALA_CODE'] == 'ES_XES70') | (df_f['AEROPUERTO_ESCALA_CODE'] == 'ES70') | (df_f['AEROPUERTO_ESCALA_CODE'] == 'FOREIGN'))]

  # Dataframe with valid airports in the source data
  istac_airports: pd.DataFrame = df_f[['AEROPUERTO_ESCALA#en', 'AEROPUERTO_ESCALA_CODE']].copy(deep=True)
  istac_airports.drop_duplicates(inplace=True)
  # Extract the airport code by removing the first three characters (country code and '_')
  istac_airports[JOIN_COL_OUR_AIRPORT] = istac_airports['AEROPUERTO_ESCALA_CODE'].str[3:]
  
  # Join istac airports with ourairports dataset to obtain the coordinates from each airport
  airport_csv: pd.DataFrame = pd.read_csv('airports.csv') # Replace this with a direct download from https://davidmegginson.github.io/ourairports-data/airports.csv
  airport_csv = airport_csv.merge(countries, on='iso_country')
  join: pd.DataFrame = istac_airports.merge(airport_csv, on=JOIN_COL_OUR_AIRPORT, suffixes=("l", "r"))

  # Output missing airports
  print(f"Mising airports: {len(istac_airports['AEROPUERTO_ESCALA#en'].unique()) - len(join['AEROPUERTO_ESCALA#en'].unique())}")
  missing_airports = set(istac_airports['AEROPUERTO_ESCALA#en'].unique()) - set(join['AEROPUERTO_ESCALA#en'].unique())
  print(f"Missing airports: {missing_airports}")
  # To date there are only 4 missing airports, 'Dakhla Airport', 'Robin Hood Doncaster Sheffield Airport', 'Hassan I Airport', 'Berlin-Tegel Airport'
  # It's not worth it changing the logic of the whole pipeline just for these 4 airports
  # For now leave it as it is (ignore these airports), if the number of missing airports
  # increases then I will look into it
  if len(missing_airports > 6):
    raise Exception("Too many missing airports")

  # Create final dataset
  result_df: pd.DataFrame = join[['AEROPUERTO_ESCALA#en', 'AEROPUERTO_ESCALA_CODE', 'latitude_deg', 'longitude_deg','iso_country', 'CountryName']].copy(deep=True)
  result_df.rename({'iso_country': 'CountryCode', 'AEROPUERTO_ESCALA#en': 'AirportName', 
                    'latitude_deg': 'Latitude', 'longitude_deg': 'Longitude', 
                    'country': 'CountryName', 'AEROPUERTO_ESCALA_CODE': 'AirportCode'}, axis=1, inplace=True)
  result_df['AirportId'] = result_df.index
  result_df.to_csv('../../data/Airport.csv', index=False)


def create_territory_aircraftmovement_airservice():
  df: pd.DataFrame = pd.read_csv(pd.read_csv(_get_data_from_API_call(LATEST_DATA_REMANING_TABLES)))
  create_territory(df)
  create_aircraftmovement(df)
  create_airservice(df)

def create_aircraftmovement(df: pd.DataFrame):
  df_am = df[['MOVIMIENTO_AERONAVE_CODE', 'MOVIMIENTO_AERONAVE#en']].drop_duplicates().reset_index(drop=True)

  df_am['AircraftMovementId'] = df_am.index

  df_am.rename({'MOVIMIENTO_AERONAVE_CODE': 'AircraftMovementCode', 'MOVIMIENTO_AERONAVE#en': 'AircraftMovement'}, axis=1, inplace=True)

  df_am = df_am[['AircraftMovementId', 'AircraftMovementCode', 'AircraftMovement']]

  df_am.to_csv('../../data/Final_AircraftMovement.csv', index=False)

def create_airservice(df: pd.DataFrame):
  df_as = df[['SERVICIO_AEREO_CODE', 'SERVICIO_AEREO#en']].drop_duplicates().reset_index(drop=True)

  df_as['AirServiceId'] = df_as.index

  df_as.rename({'SERVICIO_AEREO_CODE': 'AirServiceCode', 'SERVICIO_AEREO#en': 'AirService'}, axis=1, inplace=True)

  df_as = df_as[['AirServiceId', 'AirServiceCode','AirService']]

  df_as.to_csv('../../data/AirService.csv', index=False)

def create_territory(df: pd.DataFrame):
  
  df_terr = pd.concat([df[['TERRITORIO_CODE', 'TERRITORIO#en']], df[['AEROPUERTO_ESCALA_CODE', 'AEROPUERTO_ESCALA#en']].rename({'AEROPUERTO_ESCALA#en': 'TERRITORIO#en', 'AEROPUERTO_ESCALA_CODE': 'TERRITORIO_CODE'}, axis=1)]).drop_duplicates()
  df_terr.reset_index(inplace=True, drop=True)
  # Remove "Total", "Foreign and Spain (Canary Islands excluded)", "Spain"
  df_terr = df_terr.loc[~df_terr['TERRITORIO_CODE'].isin(["_T_XES70", "ES", "_T"])]

  df_terr['TerritoryId'] = df_terr.index
  df_terr.rename({'TERRITORIO_CODE': 'TerritoryCode', 'TERRITORIO#en': 'TerritoryName'}, inplace=True, axis=1)
  df_terr = df_terr[['TerritoryId', 'TerritoryCode', 'TerritoryName']]

  df_terr.to_csv('../../data/Final_Territory.csv', index=False)

def _month(value: str) -> date:
    year, number = (int(part) for part in value.split("-"))
    return date(year, number, 1)


def generate_calendar(start: str = "2004-01", end: str = "2099-12") -> list[dict[str, object]]:
    current, last = _month(start), _month(end)
    result = []
    while current <= last:
        quarter = (current.month - 1) // 3 + 1
        result.append({
            "MonthId": current.year * 100 + current.month,
            "MonthStartDate": current.isoformat(),
            "MonthNumber": current.month,
            "MonthName": month_name[current.month],
            "QuarterNumber": quarter,
            "QuarterName": f"Q{quarter}",
            "Year": current.year,
            "YearMonth": current.strftime("%Y-%m"),
        })
        current = date(current.year + (current.month == 12), 1 if current.month == 12 else current.month + 1, 1)
    CALENDAR_COLUMNS = ["MonthId", "MonthStartDate", "MonthNumber", "MonthName", "QuarterNumber", "QuarterName", "Year", "YearMonth"]
    #return result save result as a CSV file

if __name__ == "__main__":
   # Read from config.yaml full_history_start_month and calendar_end_month and use that to generate_calendar
   # create a main function that calls all functions 
   # Change the paths to use the data path defined in @source_new_project_2/config/config.yaml, the paths inside config are relative to the root folder (in the future all the code in source_new_project_2 will be moved to the true root folder)