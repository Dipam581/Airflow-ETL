from airflow import DAG
from airflow.providers.http.hooks.http import HttpHook
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.decorators import task
from airflow.utils.dates import days_ago

from airflow.operators.python_operator import PythonOperator
from airflow.providers.snowflake.operators.snowflake import SnowflakeOperator

import requests
import json

# Latitude and longitude for the desired location (London in this case)
LATITUDE = '51.5074'
LONGITUDE = '-0.1278'
POSTGRES_CONN_ID='postgres_default'

api_key= '45VI4ZOVBTB4TK0S'


default_args={
    'owner':'airflow',
    'start_date':days_ago(1)
}

## DAG
with DAG(dag_id='Stock_etl_pipeline',
         default_args=default_args,
         schedule_interval='@daily',
         catchup=False) as dags:
    
    @task()
    def extract_stock_data():
        """Extract weather data from Open-Meteo API using Airflow Connection."""

        # Use HTTP Hook to get connection details from Airflow connection

        url = f'https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol=RELIANCE.BSE&outputsize=full&apikey={api_key}'
        response = requests.get(url)

        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to fetch weather data: {response.status_code}")
        
    @task()
    def transform_weather_data(stock_data):
        """Transform the extracted weather data."""
        print(stock_data["Time Series (Daily)"]["2025-02-01"])
        
        return True
    
    run_query = SnowflakeOperator(
        task_id="run_query",
        snowflake_conn_id="snowflake_conn",
        sql="SELECT * FROM RAW_POS.MENU LIMIT 10;",
        dag=dags,  # Attach it to the DAG
    )
    
    @task()
    def load_weather_data(transformed_data):
        """Load transformed data into PostgreSQL."""
        pg_hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)
        conn = pg_hook.get_conn()
        cursor = conn.cursor()

        # Create table if it doesn't exist
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS weather_data (
            latitude FLOAT,
            longitude FLOAT,
            temperature FLOAT,
            windspeed FLOAT,
            winddirection FLOAT,
            weathercode INT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # Insert transformed data into the table
        cursor.execute("""
        INSERT INTO weather_data (latitude, longitude, temperature, windspeed, winddirection, weathercode)
        VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            transformed_data['latitude'],
            transformed_data['longitude'],
            transformed_data['temperature'],
            transformed_data['windspeed'],
            transformed_data['winddirection'],
            transformed_data['weathercode']
        ))

        conn.commit()
        cursor.close()

    ## DAG Worflow- ETL Pipeline
    stock_data= extract_stock_data()
    transformed_data=transform_weather_data(stock_data)
    transformed_data >> run_query
    # load_weather_data(transformed_data)

        
    




    

