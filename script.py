import requests
import csv
import os
import snowflake.connector
from dotenv import load_dotenv
from datetime import datetime
load_dotenv()

POLYGON_API_KEY = os.getenv("POLYGON_API_KEY")

# Snowflake connection parameters
SNOWFLAKE_ACCOUNT = os.getenv("SNOWFLAKE_ACCOUNT")
SNOWFLAKE_USER = os.getenv("SNOWFLAKE_USER")
SNOWFLAKE_PASSWORD = os.getenv("SNOWFLAKE_PASSWORD")
SNOWFLAKE_WAREHOUSE = os.getenv("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH")
SNOWFLAKE_DATABASE = os.getenv("SNOWFLAKE_DATABASE", "STOCK_DATA")
SNOWFLAKE_SCHEMA = os.getenv("SNOWFLAKE_SCHEMA", "PUBLIC")
ORDER = 'asc'
LIMIT = '1000'
DATE_STAMP = '2025-10-11'



def run_stock_job():
    url = f'https://api.polygon.io/v3/reference/tickers?market=stocks&active=true&order={ORDER}&limit={LIMIT}&sort=ticker&apiKey={POLYGON_API_KEY}'
    response = requests.get(url)
    tickers = []
    DATE_STAMP = datetime.now().strftime('%Y-%m-%d')

    data = response.json()
    for ticker in data['results']:
        ticker['date_stamp'] = DATE_STAMP
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
            ticker['date_stamp'] = DATE_STAMP
            tickers.append(ticker)


    print(len(tickers))

    # Write collected tickers to Snowflake
    try:
        # Connect to Snowflake
        conn = snowflake.connector.connect(
            user=SNOWFLAKE_USER,
            password=SNOWFLAKE_PASSWORD,
            account=SNOWFLAKE_ACCOUNT,
            warehouse=SNOWFLAKE_WAREHOUSE,
            database=SNOWFLAKE_DATABASE,
            schema=SNOWFLAKE_SCHEMA
        )
        
        cursor = conn.cursor()
        
        # Create table if it doesn't exist
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS stock_tickers (
            ticker VARCHAR(20),
            name VARCHAR(500),
            market VARCHAR(50),
            locale VARCHAR(10),
            primary_exchange VARCHAR(20),
            type VARCHAR(10),
            active BOOLEAN,
            currency_name VARCHAR(10),
            cik VARCHAR(20),
            composite_figi VARCHAR(20),
            share_class_figi VARCHAR(20),
            last_updated_utc TIMESTAMP_TZ,
            created_at TIMESTAMP_TZ DEFAULT CURRENT_TIMESTAMP(),
            date_stamp DATE
        )
        """
        cursor.execute(create_table_sql)
        
        # Clear existing data (optional - remove if you want to append)
        cursor.execute("DELETE FROM stock_tickers")
        
        # Insert ticker data using batch insert (much faster)
        insert_sql = """
        INSERT INTO stock_tickers (
            ticker, name, market, locale, primary_exchange, type, 
            active, currency_name, cik, composite_figi, share_class_figi, last_updated_utc, date_stamp
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        # Prepare batch data
        batch_data = []
        for ticker in tickers:
            batch_data.append((
                ticker.get('ticker'),
                ticker.get('name'),
                ticker.get('market'),
                ticker.get('locale'),
                ticker.get('primary_exchange'),
                ticker.get('type'),
                ticker.get('active'),
                ticker.get('currency_name'),
                ticker.get('cik'),
                ticker.get('composite_figi'),
                ticker.get('share_class_figi'),
                ticker.get('last_updated_utc'),
                ticker.get('date_stamp')
            ))
        
        # Execute batch insert
        cursor.executemany(insert_sql, batch_data)
        
        conn.commit()
        print(f"Successfully inserted {len(tickers)} tickers into Snowflake")
        
    except Exception as e:
        print(f"Error writing to Snowflake: {e}")
    finally:
        if 'conn' in locals():
            conn.close()


if __name__ == "__main__":
    run_stock_job()
