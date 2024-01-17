import requests
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("FINANCE_API_KEY")

def chart_data(stockName: str, start: str, end: str):
    api_endpoint = f"https://financialmodelingprep.com/api/v3/historical-chart/5min/{stockName}?from={start}&to={end}&apikey={api_key}"
    response = requests.get(api_endpoint)
    if response.status_code == 200:
        data = response.json()
        print(data)
        return data
    else:
        print(f"Error: {response.status_code}")
    