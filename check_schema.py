"""Check actual database schema"""
import asyncio
from google.cloud.sql.connector import Connector

async def check_schema():
    connector = Connector()

    try:
        conn = await connector.connect_async(
            "medical-473219:us-central1:pncp-medical-db",
            "asyncpg",
            user="postgres",
            password="TempPass123!",
            db="pncp_medical_data"
        )

        # Check tenders table columns
        result = await conn.fetch("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'tenders'
            ORDER BY ordinal_position
        """)

        print("TENDERS TABLE COLUMNS:")
        for row in result:
            print(f"  {row['column_name']}: {row['data_type']}")

        # Check tender_items columns
        result = await conn.fetch("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'tender_items'
            ORDER BY ordinal_position
        """)

        print("\nTENDER_ITEMS TABLE COLUMNS:")
        for row in result:
            print(f"  {row['column_name']}: {row['data_type']}")

        await conn.close()
    finally:
        await connector.close_async()

asyncio.run(check_schema())
