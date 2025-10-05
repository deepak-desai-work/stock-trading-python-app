import requests
import csv
import os
from dotenv import load_dotenv
load_dotenv()

POLYGON_API_KEY = os.getenv("POLYGON_API_KEY")
order = 'asc'
limit = '1000'

url = f'https://api.polygon.io/v3/reference/tickers?market=stocks&active=true&order={order}&limit={limit}&sort=ticker&apiKey={POLYGON_API_KEY}'
response = requests.get(url)
tickers = []

data = response.json()
for ticker in data['results']:
    tickers.append(ticker)

print(data)

while 'next_url' in data:
    print('Requesting next page')
    url = data['next_url'] + f'&apiKey={POLYGON_API_KEY}'
    response = requests.get(url)
    # Stop early on rate limit or non-200 responses; keep what we have
    if response.status_code == 429:
        print('Rate limit hit. Returning partial results collected so far.')
        break
    if response.status_code != 200:
        print(f'HTTP error {response.status_code}. Returning partial results.')
        break

    data = response.json()
    print(data)
    for ticker in data['results']:
        tickers.append(ticker)


example_ticker =  {
    'ticker': 'HSDT', 
    'name': 'Solana Company Class A Common Stock (DE)', 
    'market': 'stocks', 
    'locale': 'us', 
    'primary_exchange': 'XNAS', 
    'type': 'CS', 
    'active': True, 
    'currency_name': 'usd', 
    'cik': '0001610853', 
    'composite_figi': 'BBG006QSQYY6', 
    'share_class_figi': 'BBG006NXG8C0', 
    'last_updated_utc': '2025-10-05T06:05:16.272740104Z'
}

print(len(tickers))

# Write collected tickers to CSV matching example_ticker schema
fieldnames = [
    'ticker',
    'name',
    'market',
    'locale',
    'primary_exchange',
    'type',
    'active',
    'currency_name',
    'cik',
    'composite_figi',
    'share_class_figi',
    'last_updated_utc',
]

with open('tickers.csv', 'w', newline='', encoding='utf-8') as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()
    for t in tickers:
        row = {key: t.get(key) for key in fieldnames}
        writer.writerow(row)
