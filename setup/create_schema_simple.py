#!/usr/bin/env python3
"""
Simple schema creation - creates tables if they don't exist
Uses CREATE TABLE IF NOT EXISTS to avoid conflicts
"""

import asyncio
import os
from dotenv import load_dotenv
from google.cloud.sql.connector import Connector

load_dotenv()

# Simple schema statements
SCHEMA_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS organizations (
        id SERIAL PRIMARY KEY,
        cnpj VARCHAR(18) UNIQUE NOT NULL,
        name VARCHAR(500) NOT NULL,
        government_level VARCHAR(50) NOT NULL,
        organization_type VARCHAR(50),
        state_code VARCHAR(2),
        municipality_name VARCHAR(200),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS tenders (
        id SERIAL PRIMARY KEY,
        organization_id INTEGER REFERENCES organizations(id),
        cnpj VARCHAR(18) NOT NULL,
        ano INTEGER NOT NULL,
        sequencial INTEGER NOT NULL,
        control_number VARCHAR(50) UNIQUE,
        title VARCHAR(1000),
        description TEXT,
        government_level VARCHAR(50) NOT NULL,
        tender_size VARCHAR(20) NOT NULL,
        contracting_modality INTEGER,
        modality_name VARCHAR(100),
        total_estimated_value DECIMAL(15,2),
        total_homologated_value DECIMAL(15,2),
        publication_date DATE,
        state_code VARCHAR(2),
        municipality_code VARCHAR(10),
        status VARCHAR(50) DEFAULT 'discovered',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS tender_items (
        id SERIAL PRIMARY KEY,
        tender_id INTEGER REFERENCES tenders(id),
        item_number INTEGER,
        description TEXT,
        quantity DECIMAL(15,3),
        unit VARCHAR(50),
        unit_price DECIMAL(15,2),
        total_price DECIMAL(15,2),
        matched_product_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS matched_products (
        id SERIAL PRIMARY KEY,
        tender_item_id INTEGER REFERENCES tender_items(id),
        product_code VARCHAR(100),
        product_name VARCHAR(500),
        match_score DECIMAL(5,2),
        fob_price_usd DECIMAL(15,2),
        fob_price_brl DECIMAL(15,2),
        price_difference_pct DECIMAL(5,2),
        is_competitive BOOLEAN,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS processing_log (
        id SERIAL PRIMARY KEY,
        process_type VARCHAR(100),
        state_code VARCHAR(2),
        status VARCHAR(50),
        records_processed INTEGER DEFAULT 0,
        records_matched INTEGER DEFAULT 0,
        started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        completed_at TIMESTAMP,
        error_message TEXT,
        metadata JSONB
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS homologated_results (
        id SERIAL PRIMARY KEY,
        tender_id INTEGER REFERENCES tenders(id),
        item_number INTEGER,
        supplier_cnpj VARCHAR(18),
        supplier_name VARCHAR(500),
        homologated_unit_price DECIMAL(15,2),
        homologated_quantity DECIMAL(15,3),
        homologated_total_price DECIMAL(15,2),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """
]

async def create_schema():
    """Create database schema"""

    project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
    region = os.getenv('CLOUD_SQL_REGION')
    instance_name = os.getenv('CLOUD_SQL_INSTANCE')
    database_name = os.getenv('DATABASE_NAME')

    connection_name = f"{project_id}:{region}:{instance_name}"

    print("=" * 70)
    print("Creating Database Schema")
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
            db="postgres",  # Connect to postgres database first
            enable_iam_auth=True,
            ip_type="public"
        )
        print("   ✅ Connected to postgres database")

        # Check if our database exists
        print(f"\n2️⃣  Checking if database '{database_name}' exists...")
        exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1",
            database_name
        )

        if not exists:
            print(f"   Creating database '{database_name}'...")
            # Need to close current connection to create database
            await conn.close()

            # Reconnect and create
            conn = await connector.connect_async(
                instance_connection_string=connection_name,
                driver="asyncpg",
                user=os.getenv('DB_USER'),
                db="postgres",
                enable_iam_auth=True,
                ip_type="public"
            )

            await conn.execute(f'CREATE DATABASE {database_name}')
            print(f"   ✅ Database created")
        else:
            print(f"   ✅ Database exists")

        await conn.close()

        # Now connect to our database and create tables
        print(f"\n3️⃣  Connecting to '{database_name}'...")
        conn = await connector.connect_async(
            instance_connection_string=connection_name,
            driver="asyncpg",
            user=os.getenv('DB_USER'),
            db=database_name,
            enable_iam_auth=True,
            ip_type="public"
        )
        print("   ✅ Connected")

        print("\n4️⃣  Creating tables...")
        table_names = ['organizations', 'tenders', 'tender_items', 'matched_products', 'processing_log', 'homologated_results']

        for i, (stmt, table_name) in enumerate(zip(SCHEMA_STATEMENTS, table_names), 1):
            try:
                await conn.execute(stmt)
                print(f"   ✅ {i}. {table_name}")
            except Exception as e:
                print(f"   ❌ {i}. {table_name}: {e}")

        print("\n5️⃣  Verifying tables...")
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
        print("✅ Schema Creation Complete!")
        print("=" * 70)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        raise

    finally:
        await connector.close_async()

if __name__ == "__main__":
    asyncio.run(create_schema())