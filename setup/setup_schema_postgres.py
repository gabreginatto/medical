#!/usr/bin/env python3
"""
Setup schema using postgres user and grant permissions to service account
"""

import asyncio
from dotenv import load_dotenv
from google.cloud.sql.connector import Connector
import os

load_dotenv()

# Table definitions (abbreviated for speed)
SCHEMA_SQL = open('schema.sql', 'r').read()

async def setup():
    """Create schema using postgres user"""

    project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
    region = os.getenv('CLOUD_SQL_REGION')
    instance_name = os.getenv('CLOUD_SQL_INSTANCE')
    database_name = os.getenv('DATABASE_NAME')
    service_account_user = "pncp-medical-app@medical-473219.iam"

    connection_name = f"{project_id}:{region}:{instance_name}"

    print("=" * 70)
    print("Setup Database Schema")
    print("=" * 70)

    connector = Connector()

    try:
        print("\n1️⃣  Connecting as postgres...")
        conn = await connector.connect_async(
            instance_connection_string=connection_name,
            driver="asyncpg",
            user="postgres",
            password="TempPass123!",
            db=database_name,
            ip_type="public"
        )
        print("   ✅ Connected")

        print("\n2️⃣  Creating tables...")
        statements = [s.strip() for s in SCHEMA_SQL.split(';') if s.strip() and 'CREATE TABLE' in s.upper()]

        for stmt in statements:
            try:
                await conn.execute(stmt)
                # Extract table name
                if 'IF NOT EXISTS' in stmt.upper():
                    table_name = stmt.split('IF NOT EXISTS')[1].split('(')[0].strip()
                else:
                    table_name = stmt.split('CREATE TABLE')[1].split('(')[0].strip()
                print(f"   ✅ {table_name}")
            except Exception as e:
                print(f"   ⚠️  Error: {e}")

        print("\n3️⃣  Granting permissions to service account...")
        await conn.execute(f'GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO "{service_account_user}"')
        await conn.execute(f'GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO "{service_account_user}"')
        await conn.execute(f'ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO "{service_account_user}"')
        await conn.execute(f'ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO "{service_account_user}"')
        print(f"   ✅ Granted all privileges to {service_account_user}")

        print("\n4️⃣  Verifying...")
        tables = await conn.fetch("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name")
        print(f"   ✅ {len(tables)} tables created:")
        for t in tables:
            print(f"      - {t['table_name']}")

        await conn.close()

        print("\n" + "=" * 70)
        print("✅ Setup Complete!")
        print("=" * 70)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        raise
    finally:
        await connector.close_async()

if __name__ == "__main__":
    asyncio.run(setup())