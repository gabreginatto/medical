#!/usr/bin/env python3
"""
Initialize Database Schema
Creates all tables needed for the PNCP Medical Data Processor
"""

import asyncio
import os
from dotenv import load_dotenv
from google.cloud.sql.connector import Connector

load_dotenv()

async def initialize_database():
    """Create database schema"""

    project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
    region = os.getenv('CLOUD_SQL_REGION')
    instance_name = os.getenv('CLOUD_SQL_INSTANCE')
    database_name = os.getenv('DATABASE_NAME')

    connection_name = f"{project_id}:{region}:{instance_name}"

    print("=" * 70)
    print("Initializing Database Schema")
    print("=" * 70)
    print(f"\nConnection: {connection_name}")
    print(f"Database: {database_name}")

    connector = Connector()

    try:
        print("\n1️⃣  Connecting to Cloud SQL...")
        conn = await connector.connect_async(
            instance_connection_string=connection_name,
            driver="asyncpg",
            user=os.getenv('DB_USER'),
            db=database_name,
            enable_iam_auth=True,
            ip_type="public"
        )
        print("   ✅ Connected successfully")

        print("\n2️⃣  Reading schema.sql file...")
        with open('schema.sql', 'r') as f:
            schema_sql = f.read()
        print("   ✅ Schema file loaded")

        print("\n3️⃣  Creating database tables...")

        # Split schema into individual statements and execute one by one
        statements = [stmt.strip() for stmt in schema_sql.split(';') if stmt.strip()]

        for i, stmt in enumerate(statements, 1):
            if stmt:
                try:
                    await conn.execute(stmt)
                    # Print progress for CREATE TABLE statements
                    if 'CREATE TABLE' in stmt.upper():
                        table_name = stmt.split('CREATE TABLE')[1].split('IF NOT EXISTS')[1].split('(')[0].strip() if 'IF NOT EXISTS' in stmt.upper() else stmt.split('CREATE TABLE')[1].split('(')[0].strip()
                        print(f"      ✅ Created table: {table_name}")
                except Exception as e:
                    print(f"      ⚠️  Statement {i} warning: {e}")

        print("   ✅ Schema execution completed")

        print("\n4️⃣  Verifying tables...")
        tables = await conn.fetch("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)

        print(f"   ✅ Found {len(tables)} tables:")
        for table in tables:
            print(f"      - {table['table_name']}")

        await conn.close()

        print("\n" + "=" * 70)
        print("✅ Database Initialization Complete!")
        print("=" * 70)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        raise

    finally:
        await connector.close_async()

if __name__ == "__main__":
    asyncio.run(initialize_database())