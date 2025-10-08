"""Refresh all analytics materialized views"""
import asyncio
from google.cloud.sql.connector import Connector

async def refresh_all():
    connector = Connector()

    try:
        conn = await connector.connect_async(
            "medical-473219:us-central1:pncp-medical-db",
            "asyncpg",
            user="postgres",
            password="TempPass123!",
            db="pncp_medical_data"
        )

        print("Refreshing all analytics views...\n")

        # Refresh each view
        views = [
            'analytics.curativo_items',
            'analytics.medical_items_summary',
            'analytics.state_summary',
            'analytics.top_winners',
            'analytics.super_tenders'
        ]

        for view in views:
            print(f"Refreshing {view}...")
            await conn.execute(f"REFRESH MATERIALIZED VIEW {view}")

            # Count rows
            result = await conn.fetchval(f"SELECT COUNT(*) FROM {view}")
            print(f"  ✅ {result} rows\n")

        print("✅ All views refreshed successfully!")

        await conn.close()
    finally:
        await connector.close_async()

asyncio.run(refresh_all())
