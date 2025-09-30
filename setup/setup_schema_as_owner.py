#!/usr/bin/env python3
"""
Setup schema using owner account and grant permissions to service account
"""

import asyncio
import os
from dotenv import load_dotenv
from google.cloud.sql.connector import Connector

load_dotenv()

# Table creation statements
TABLES = {
    'organizations': """
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
    'tenders': """
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
    'tender_items': """
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
    'matched_products': """
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
    'processing_log': """
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
    'homologated_results': """
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
}

async def setup_schema():
    """Create schema using owner account"""

    project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
    region = os.getenv('CLOUD_SQL_REGION')
    instance_name = os.getenv('CLOUD_SQL_INSTANCE')
    database_name = os.getenv('DATABASE_NAME')
    service_account_user = "pncp-medical-app@medical-473219.iam"

    connection_name = f"{project_id}:{region}:{instance_name}"

    print("=" * 70)
    print("Setup Database Schema (as Owner)")
    print("=" * 70)
    print(f"\nConnection: {connection_name}")
    print(f"Database: {database_name}")
    print(f"User: gabrielreginatto@gmail.com (owner)")

    connector = Connector()

    try:
        print("\n1️⃣  Connecting to Cloud SQL as owner...")
        conn = await connector.connect_async(
            instance_connection_string=connection_name,
            driver="asyncpg",
            user="gabrielreginatto@gmail.com",
            db=database_name,
            enable_iam_auth=True,
            ip_type="public"
        )
        print("   ✅ Connected successfully")

        print("\n2️⃣  Creating tables...")
        for table_name, create_stmt in TABLES.items():
            try:
                await conn.execute(create_stmt)
                print(f"   ✅ {table_name}")
            except Exception as e:
                print(f"   ⚠️  {table_name}: {e}")

        print("\n3️⃣  Granting permissions to service account...")
        print(f"   Service Account: {service_account_user}")

        # Grant all permissions on all tables
        await conn.execute(f'GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO "{service_account_user}"')
        print("   ✅ Granted ALL on tables")

        # Grant all permissions on all sequences
        await conn.execute(f'GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO "{service_account_user}"')
        print("   ✅ Granted ALL on sequences")

        # Grant default privileges for future objects
        await conn.execute(f'ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON TABLES TO "{service_account_user}"')
        print("   ✅ Granted default privileges on tables")

        await conn.execute(f'ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON SEQUENCES TO "{service_account_user}"')
        print("   ✅ Granted default privileges on sequences")

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
        print("✅ Schema Setup Complete!")
        print("=" * 70)
        print(f"\nService account '{service_account_user}' now has:")
        print("  • ALL privileges on all tables")
        print("  • ALL privileges on all sequences")
        print("  • Default privileges for future objects")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        raise

    finally:
        await connector.close_async()

if __name__ == "__main__":
    asyncio.run(setup_schema())