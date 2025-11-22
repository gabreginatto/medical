#!/usr/bin/env python3
"""
Create filtered views with min/max value ranges for Looker Studio
"""
import asyncio
import asyncpg

async def create_filtered_views():
    conn = await asyncpg.connect(
        host='34.134.110.78',
        port=5432,
        database='pncp_medical_data',
        user='postgres',
        password='TempPass123!'
    )

    print("Creating value-filtered views...\n")

    # View 1: Curativos with reasonable values (R$1 to R$10,000 per unit)
    await conn.execute("""
        CREATE OR REPLACE VIEW vw_curativos_reasonable_prices AS
        SELECT * FROM vw_curativos
        WHERE homologated_unit_value BETWEEN 1 AND 10000;
    """)

    count1 = await conn.fetchval("SELECT COUNT(*) FROM vw_curativos_reasonable_prices")
    original1 = await conn.fetchval("SELECT COUNT(*) FROM vw_curativos")

    print(f"✅ vw_curativos_reasonable_prices")
    print(f"   Filter: R$1 - R$10,000 per unit")
    print(f"   Original: {original1:,} rows")
    print(f"   Filtered: {count1:,} rows")
    print(f"   Excluded: {original1 - count1:,} rows\n")

    # View 2: All items with reasonable values
    await conn.execute("""
        CREATE OR REPLACE VIEW vw_items_reasonable_prices AS
        SELECT * FROM vw_tender_items_complete
        WHERE homologated_unit_value BETWEEN 1 AND 10000;
    """)

    count2 = await conn.fetchval("SELECT COUNT(*) FROM vw_items_reasonable_prices")
    original2 = await conn.fetchval("SELECT COUNT(*) FROM vw_tender_items_complete")

    print(f"✅ vw_items_reasonable_prices")
    print(f"   Filter: R$1 - R$10,000 per unit")
    print(f"   Original: {original2:,} rows")
    print(f"   Filtered: {count2:,} rows")
    print(f"   Excluded: {original2 - count2:,} rows\n")

    # View 3: MDSAP items with reasonable values
    await conn.execute("""
        CREATE OR REPLACE VIEW vw_mdsap_items_reasonable_prices AS
        SELECT * FROM vw_mdsap_items
        WHERE homologated_unit_value BETWEEN 1 AND 10000;
    """)

    count3 = await conn.fetchval("SELECT COUNT(*) FROM vw_mdsap_items_reasonable_prices")
    original3 = await conn.fetchval("SELECT COUNT(*) FROM vw_mdsap_items")

    print(f"✅ vw_mdsap_items_reasonable_prices")
    print(f"   Filter: R$1 - R$10,000 per unit")
    print(f"   Original: {original3:,} rows")
    print(f"   Filtered: {count3:,} rows")
    print(f"   Excluded: {original3 - count3:,} rows\n")

    print("=" * 60)
    print("✅ Done! New views created:")
    print("   • vw_curativos_reasonable_prices")
    print("   • vw_items_reasonable_prices")
    print("   • vw_mdsap_items_reasonable_prices")
    print("\nUse these in Looker Studio to automatically filter out")
    print("extreme values (< R$1 or > R$10,000 per unit)")
    print("=" * 60)

    await conn.close()

if __name__ == "__main__":
    asyncio.run(create_filtered_views())
