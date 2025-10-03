#!/usr/bin/env python3
"""
Verify data in database
"""

import asyncio
from database import create_db_manager_from_env
from dotenv import load_dotenv

load_dotenv()

async def verify_database():
    """Query database to verify tenders were saved"""

    db_manager = create_db_manager_from_env()

    try:
        conn = await db_manager.get_connection()

        print("=" * 70)
        print("🔍 DATABASE VERIFICATION")
        print("=" * 70)

        # Check organizations
        print("\n📋 ORGANIZATIONS:")
        orgs = await conn.fetch("SELECT * FROM organizations ORDER BY id")
        print(f"   Total organizations: {len(orgs)}")
        for org in orgs:
            print(f"\n   ID: {org['id']}")
            print(f"   CNPJ: {org['cnpj']}")
            print(f"   Name: {org['name']}")
            print(f"   Government Level: {org.get('government_level', 'N/A')}")
            print(f"   State: {org.get('state_code', 'N/A')}")

        # Check tenders
        print("\n\n📋 TENDERS:")
        tenders = await conn.fetch("""
            SELECT t.*, o.name as org_name, o.cnpj
            FROM tenders t
            JOIN organizations o ON t.organization_id = o.id
            ORDER BY t.id
        """)
        print(f"   Total tenders: {len(tenders)}")
        for tender in tenders:
            print(f"\n   ID: {tender['id']}")
            print(f"   Control Number: {tender['control_number']}")
            print(f"   Organization: {tender['org_name']}")
            print(f"   CNPJ: {tender['cnpj']}")

        # Get table schema
        print("\n\n📋 TENDERS TABLE SCHEMA:")
        columns = await conn.fetch("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'tenders'
            ORDER BY ordinal_position
        """)
        for col in columns:
            print(f"   - {col['column_name']}: {col['data_type']}")

        print("\n" + "=" * 70)
        if len(tenders) > 0:
            print("✅ SUCCESS - Data verified in database!")
        else:
            print("⚠️  WARNING - No tenders found in database")
        print("=" * 70)

        await conn.close()

    finally:
        await db_manager.close()

if __name__ == "__main__":
    asyncio.run(verify_database())
