import asyncio
from google.cloud.sql.connector import Connector

async def check():
    connector = Connector()
    conn = await connector.connect_async('medical-473219:us-central1:pncp-medical-db', 'asyncpg', user='postgres', password='TempPass123!', db='pncp_medical_data')

    # Check if matched_products table exists
    result = await conn.fetch("SELECT table_name FROM information_schema.tables WHERE table_name = 'matched_products';")
    if result:
        print('matched_products table EXISTS')
        cols = await conn.fetch("SELECT column_name FROM information_schema.columns WHERE table_name = 'matched_products'")
        print('Columns:')
        for row in cols:
            print(f'  {row["column_name"]}')
    else:
        print('matched_products table DOES NOT EXIST')

    await conn.close()
    await connector.close_async()

asyncio.run(check())
