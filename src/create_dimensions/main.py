from calendar import month_name
from datetime import date
from pathlib import Path
import sys
import tempfile

import pandas as pd
import requests

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "air_transport_statistics"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from load_config.config import load_config

def _read_csv_from_url(url: str, request_timeout: float, usecols: list[str] | None = None) -> pd.DataFrame:
    with requests.get(url, stream=True, timeout=request_timeout) as response:
        response.raise_for_status()
        with tempfile.NamedTemporaryFile(mode="wb", suffix=".csv") as temporary_file:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    temporary_file.write(chunk)
            temporary_file.flush()
            return pd.read_csv(temporary_file.name, usecols=usecols)

# https://www3.gobiernodecanarias.org/istac/statistical-visualizer/visualizer/data.html?resourceType=dataset&agencyId=ISTAC&resourceId=C00017A_000001&version=%7Elatest&multidatasetId=ISTAC%3AC00017A_000001#visualization/table
LATEST_DATA_AIRPORTS = "https://datos.canarias.es/api/estadisticas/statistical-resources/v1.0/datasets/ISTAC/C00017A_000001/~latest.csv?lang=en"
# https://www3.gobiernodecanarias.org/istac/statistical-visualizer/visualizer/data.html?resourceType=dataset&agencyId=ISTAC&resourceId=C00017A_000013&version=%7Elatest&multidatasetId=ISTAC%3AC00017A_000004#visualization/table
LATEST_DATA_REMANING_TABLES = "https://datos.canarias.es/api/estadisticas/statistical-resources/v1.0/datasets/ISTAC/C00017A_000013/~latest.csv?lang=en"

OURAIRPORTS_AIRPORTS_CSV = "https://davidmegginson.github.io/ourairports-data/airports.csv"
# Airport code column in ourairports dataset
JOIN_COL_OUR_AIRPORT = 'ident' 

def create_airports(data_dir: Path, request_timeout: float):
  df: pd.DataFrame = _read_csv_from_url(
      LATEST_DATA_AIRPORTS,
      request_timeout=request_timeout,
      usecols=['AEROPUERTO_ESCALA#en', 'AEROPUERTO_ESCALA_CODE'],
  )

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
  airport_csv: pd.DataFrame = _read_csv_from_url(
      OURAIRPORTS_AIRPORTS_CSV,
      request_timeout=request_timeout,
      usecols=[JOIN_COL_OUR_AIRPORT, 'latitude_deg', 'longitude_deg', 'iso_country'],
  )
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
  if len(missing_airports) > 6:
    raise Exception("Too many missing airports")

  # Create final dataset
  result_df: pd.DataFrame = join[['AEROPUERTO_ESCALA#en', 'AEROPUERTO_ESCALA_CODE', 'latitude_deg', 'longitude_deg','iso_country', 'CountryName']].copy(deep=True)
  result_df.rename({'iso_country': 'CountryCode', 'AEROPUERTO_ESCALA#en': 'AirportName', 
                    'latitude_deg': 'Latitude', 'longitude_deg': 'Longitude', 
                    'country': 'CountryName', 'AEROPUERTO_ESCALA_CODE': 'AirportCode'}, axis=1, inplace=True)
  result_df['AirportId'] = result_df.index
  result_df.to_csv(data_dir / 'Airport.csv', index=False)


def create_territory_aircraftmovement_airservice(data_dir: Path, request_timeout: float):
  df: pd.DataFrame = _read_csv_from_url(
      LATEST_DATA_REMANING_TABLES,
      request_timeout=request_timeout,
      usecols=[
          'MOVIMIENTO_AERONAVE_CODE',
          'MOVIMIENTO_AERONAVE#en',
          'SERVICIO_AEREO_CODE',
          'SERVICIO_AEREO#en',
          'TERRITORIO_CODE',
          'TERRITORIO#en',
          'AEROPUERTO_ESCALA_CODE',
          'AEROPUERTO_ESCALA#en',
      ],
  )
  create_territory(df, data_dir)
  create_aircraftmovement(df, data_dir)
  create_airservice(df, data_dir)

def create_aircraftmovement(df: pd.DataFrame, data_dir: Path):
  df_am = df[['MOVIMIENTO_AERONAVE_CODE', 'MOVIMIENTO_AERONAVE#en']].drop_duplicates().reset_index(drop=True)

  df_am['AircraftMovementId'] = df_am.index

  df_am.rename({'MOVIMIENTO_AERONAVE_CODE': 'AircraftMovementCode', 'MOVIMIENTO_AERONAVE#en': 'AircraftMovement'}, axis=1, inplace=True)

  df_am = df_am[['AircraftMovementId', 'AircraftMovementCode', 'AircraftMovement']]

  df_am.to_csv(data_dir / 'AircraftMovement.csv', index=False)

def create_airservice(df: pd.DataFrame, data_dir: Path):
  df_as = df[['SERVICIO_AEREO_CODE', 'SERVICIO_AEREO#en']].drop_duplicates().reset_index(drop=True)

  df_as['AirServiceId'] = df_as.index

  df_as.rename({'SERVICIO_AEREO_CODE': 'AirServiceCode', 'SERVICIO_AEREO#en': 'AirService'}, axis=1, inplace=True)

  df_as = df_as[['AirServiceId', 'AirServiceCode','AirService']]

  df_as.to_csv(data_dir / 'AirService.csv', index=False)

def create_territory(df: pd.DataFrame, data_dir: Path):
  
  df_terr = pd.concat([df[['TERRITORIO_CODE', 'TERRITORIO#en']], df[['AEROPUERTO_ESCALA_CODE', 'AEROPUERTO_ESCALA#en']].rename({'AEROPUERTO_ESCALA#en': 'TERRITORIO#en', 'AEROPUERTO_ESCALA_CODE': 'TERRITORIO_CODE'}, axis=1)]).drop_duplicates()
  df_terr.reset_index(inplace=True, drop=True)
  # Remove "Total", "Foreign and Spain (Canary Islands excluded)", "Spain"
  df_terr = df_terr.loc[~df_terr['TERRITORIO_CODE'].isin(["_T_XES70", "ES", "_T"])]

  df_terr['TerritoryId'] = df_terr.index
  df_terr.rename({'TERRITORIO_CODE': 'TerritoryCode', 'TERRITORIO#en': 'TerritoryName'}, inplace=True, axis=1)
  df_terr = df_terr[['TerritoryId', 'TerritoryCode', 'TerritoryName']]

  df_terr.to_csv(data_dir / 'Territory.csv', index=False)

def _month(value: str) -> date:
    year, number = (int(part) for part in value.split("-"))
    return date(year, number, 1)


def generate_calendar(data_dir: Path, start: str = "2004-01", end: str = "2099-12") -> pd.DataFrame:
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
    calendar_columns = ["MonthId", "MonthStartDate", "MonthNumber", "MonthName", "QuarterNumber", "QuarterName", "Year", "YearMonth"]
    calendar_df = pd.DataFrame(result, columns=calendar_columns)
    calendar_df.to_csv(data_dir / 'CalendarMonth.csv', index=False)
    return calendar_df


def main() -> None:
    config = load_config()
    data_dir = config.paths.data
    data_dir.mkdir(parents=True, exist_ok=True)

    create_airports(data_dir, config.request_timeout)
    create_territory_aircraftmovement_airservice(data_dir, config.request_timeout)
    generate_calendar(
        data_dir=data_dir,
        start=config.full_history_start_month,
        end=config.calendar_end_month,
    )

if __name__ == "__main__":
   main()
