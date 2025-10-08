"""
Run analytics views SQL setup on Cloud SQL database
"""
import asyncio
import asyncpg
import os
from google.cloud.sql.connector import Connector

async def run_sql_file():
    """Execute analytics_views.sql on Cloud SQL"""

    # Read SQL file
    sql_file_path = "/Users/gabrielreginatto/Desktop/Code/Medical/analytics_views.sql"
    print(f"Reading SQL file: {sql_file_path}")

    with open(sql_file_path, 'r') as f:
        sql_content = f.read()

    print(f"SQL file loaded ({len(sql_content)} characters)")

    # Cloud SQL connection details
    project_id = "medical-473219"
    region = "us-central1"
    instance_name = "pncp-medical-db"
    connection_name = f"{project_id}:{region}:{instance_name}"
    database = "pncp_medical_data"

    connector = Connector()

    try:
        print(f"Connecting to Cloud SQL: {connection_name}")
        print("Using password authentication...")
        conn = await connector.connect_async(
            connection_name,
            "asyncpg",
            user="postgres",
            password="TempPass123!",
            db=database
        )

        print("Connected successfully!")
        print("Executing SQL file...")

        # Execute SQL
        await conn.execute(sql_content)

        print("✅ Analytics schema and views created successfully!")

        # Verify what was created
        print("\nVerifying created views...")
        result = await conn.fetch("""
            SELECT matviewname
            FROM pg_matviews
            WHERE schemaname = 'analytics'
            ORDER BY matviewname
        """)

        print(f"\n📊 Created {len(result)} materialized views:")
        for row in result:
            print(f"   - analytics.{row['matviewname']}")

        await conn.close()

    except Exception as e:
        print(f"❌ Error: {e}")
        raise
    finally:
        await connector.close_async()

if __name__ == "__main__":
    asyncio.run(run_sql_file())
