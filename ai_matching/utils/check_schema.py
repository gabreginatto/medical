#!/usr/bin/env python3
"""
Check database schema for AI matching requirements
Verifies tables and columns needed for the matching workflow
"""

import asyncio
from dotenv import load_dotenv
from database import create_db_manager_from_env

load_dotenv()


async def check_schema():
    """Check database schema for matching requirements"""

    print("=" * 70)
    print("🔍 CHECKING DATABASE SCHEMA FOR AI MATCHING")
    print("=" * 70)

    db_manager = create_db_manager_from_env()

    try:
        conn = await db_manager.get_connection()

        # Check tender_items table
        print("\n1️⃣ Checking tender_items table...")
        tender_items_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'tender_items'
            )
        """)

        if tender_items_exists:
            print("   ✅ tender_items table exists")

            # Check columns
            columns = await conn.fetch("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = 'tender_items'
            """)

            required_cols = ['id', 'description', 'quantity', 'unit', 'homologated_unit_value', 'tender_id']
            existing_cols = [col['column_name'] for col in columns]

            for col in required_cols:
                if col in existing_cols:
                    print(f"   ✅ Column '{col}' exists")
                else:
                    print(f"   ❌ Column '{col}' MISSING")
        else:
            print("   ❌ tender_items table MISSING")

        # Check matched_products table
        print("\n2️⃣ Checking matched_products table...")
        matched_products_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'matched_products'
            )
        """)

        if matched_products_exists:
            print("   ✅ matched_products table exists")

            # Check columns
            columns = await conn.fetch("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = 'matched_products'
            """)

            required_cols = ['id', 'tender_item_id', 'fernandes_product_id', 'match_confidence', 'match_method', 'price_difference_percent']
            existing_cols = [col['column_name'] for col in columns]

            for col in required_cols:
                if col in existing_cols:
                    print(f"   ✅ Column '{col}' exists")
                else:
                    print(f"   ❌ Column '{col}' MISSING - needs to be added")
        else:
            print("   ⚠️  matched_products table does not exist")
            print("   Creating table...")

            # Create matched_products table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS matched_products (
                    id SERIAL PRIMARY KEY,
                    tender_item_id INTEGER REFERENCES tender_items(id),
                    fernandes_product_id INTEGER REFERENCES fernandes_products(id),
                    match_confidence INTEGER,
                    match_method VARCHAR(50),
                    match_reasoning TEXT,
                    price_difference_percent DECIMAL(10, 2),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(tender_item_id, fernandes_product_id)
                )
            """)
            print("   ✅ Created matched_products table")

        # Check fernandes_products table
        print("\n3️⃣ Checking fernandes_products table...")
        fernandes_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'fernandes_products'
            )
        """)

        if fernandes_exists:
            print("   ✅ fernandes_products table exists")

            # Count products
            count = await conn.fetchval("SELECT COUNT(*) FROM fernandes_products")
            print(f"   📦 Contains {count} products")

            if count == 0:
                print("   ⚠️  Table is empty - you need to load Fernandes catalog")
        else:
            print("   ⚠️  fernandes_products table does not exist")
            print("   Creating table...")

            # Create fernandes_products table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS fernandes_products (
                    id SERIAL PRIMARY KEY,
                    code VARCHAR(50) UNIQUE NOT NULL,
                    name VARCHAR(255) NOT NULL,
                    price DECIMAL(10, 2),
                    category VARCHAR(100),
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            print("   ✅ Created fernandes_products table")
            print("   ⚠️  Table is empty - you need to load Fernandes catalog")

        # Check data availability
        print("\n4️⃣ Checking data availability...")

        # Count total items
        total_items = await conn.fetchval("SELECT COUNT(*) FROM tender_items")
        print(f"   Total tender items: {total_items:,}")

        # Count items with homologated values
        items_with_price = await conn.fetchval("""
            SELECT COUNT(*)
            FROM tender_items
            WHERE homologated_unit_value IS NOT NULL
              AND homologated_unit_value > 0
        """)
        print(f"   Items with homologated prices: {items_with_price:,}")

        # Count filtered items (curativo or transparente)
        filtered_items = await conn.fetchval("""
            SELECT COUNT(*)
            FROM tender_items
            WHERE LOWER(description) LIKE '%curativo%'
               OR LOWER(description) LIKE '%transparente%'
        """)
        print(f"   Items matching filters: {filtered_items:,}")

        # Summary
        print("\n" + "=" * 70)
        print("📊 SCHEMA CHECK SUMMARY")
        print("=" * 70)

        all_good = (
            tender_items_exists and
            matched_products_exists and
            fernandes_exists and
            filtered_items > 0
        )

        if all_good:
            print("✅ Database schema is ready for AI matching!")
            print(f"\n📋 Next steps:")
            print(f"   1. Ensure Fernandes catalog is loaded (check fernandes_products table)")
            print(f"   2. Run: python3 ai_matching_step1_extract.py")
        else:
            print("⚠️  Database schema needs attention:")
            if not tender_items_exists:
                print("   - tender_items table is missing")
            if not matched_products_exists:
                print("   - matched_products table was created")
            if not fernandes_exists:
                print("   - fernandes_products table was created and needs data")
            if filtered_items == 0:
                print("   - No items match the filters (curativo/transparente)")

        await conn.close()

    finally:
        await db_manager.close()


if __name__ == "__main__":
    asyncio.run(check_schema())
