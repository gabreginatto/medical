#!/usr/bin/env python3
"""
Check if tender items table exists and contains data
"""

import asyncio
from database import create_db_manager_from_env
from dotenv import load_dotenv

load_dotenv()

async def check_items():
    db_manager = create_db_manager_from_env()

    try:
        conn = await db_manager.get_connection()

        print("=" * 70)
        print("🔍 DATABASE SCHEMA CHECK")
        print("=" * 70)

        # Check all tables
        tables = await conn.fetch("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)

        print("\n📋 TABLES IN DATABASE:")
        for table in tables:
            print(f"   - {table['table_name']}")

        # Check if items table exists
        items_table_exists = any(t['table_name'] == 'tender_items' for t in tables)

        if items_table_exists:
            print("\n\n📦 TENDER_ITEMS TABLE SCHEMA:")
            columns = await conn.fetch("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = 'tender_items'
                ORDER BY ordinal_position
            """)
            for col in columns:
                print(f"   - {col['column_name']}: {col['data_type']}")

            # Count items
            item_count = await conn.fetchval("SELECT COUNT(*) FROM tender_items")
            print(f"\n📊 TOTAL ITEMS IN DATABASE: {item_count}")

            if item_count > 0:
                # Show sample items
                print("\n📦 SAMPLE ITEMS (first 5):")
                items = await conn.fetch("""
                    SELECT id, tender_id, item_number, description, quantity, unit_value
                    FROM tender_items
                    ORDER BY id
                    LIMIT 5
                """)
                for item in items:
                    print(f"\n   Item ID: {item['id']}")
                    print(f"   Tender ID: {item['tender_id']}")
                    print(f"   Description: {item['description'][:60]}...")
                    print(f"   Quantity: {item['quantity']}")
                    print(f"   Unit Value: R$ {item['unit_value']:,.2f}" if item['unit_value'] else "   Unit Value: N/A")
            else:
                print("\n   ⚠️  Table exists but contains 0 items")
        else:
            print("\n\n⚠️  WARNING: tender_items table does NOT exist in database")
            print("   Items are NOT being saved")

        print("\n" + "=" * 70)

        await conn.close()

    finally:
        await db_manager.close()

if __name__ == "__main__":
    asyncio.run(check_items())
