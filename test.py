import requests
import pandas as pd
from io import StringIO

# URL of the CSV API
url = "https://datos.canarias.es/api/estadisticas/statistical-resources/v1.0/datasets/ISTAC/C00017A_000013/~latest.csv"

# Send HTTP GET request
response = requests.get(url)

# Check if the request was successful
if response.status_code == 200:
    # Read CSV data using pandas
    csv_data = StringIO(response.content.decode("utf-8"))
    df = pd.read_csv(csv_data)

    # Display the first few rows
    print(df.tail())
    print(df.columns)
else:
    print("Failed to retrieve data. Status code:", response.status_code)