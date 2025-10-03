#!/usr/bin/env python3
import asyncio
from database import create_db_manager_from_env
from dotenv import load_dotenv

load_dotenv()

async def show_items():
    db_manager = create_db_manager_from_env()
    conn = await db_manager.get_connection()

    print("=" * 70)
    print("📦 SAMPLE TENDER ITEMS WITH PRICES")
    print("=" * 70)

    items = await conn.fetch("""
        SELECT
            description,
            quantity,
            estimated_unit_value,
            homologated_unit_value,
            homologated_total_value,
            winner_name
        FROM tender_items
        WHERE homologated_unit_value IS NOT NULL
        LIMIT 10
    """)

    for i, item in enumerate(items, 1):
        print(f"\n{i}. {item['description'][:70]}")
        print(f"   Quantity: {item['quantity']}")
        print(f"   Estimated Price: R$ {item['estimated_unit_value']:,.2f}" if item['estimated_unit_value'] else "   Estimated Price: N/A")
        print(f"   Homologated Price: R$ {item['homologated_unit_value']:,.2f}")
        print(f"   Total Value: R$ {item['homologated_total_value']:,.2f}")
        if item['winner_name']:
            print(f"   Winner: {item['winner_name'][:50]}")

    print("\n" + "=" * 70)

    await conn.close()
    await db_manager.close()

asyncio.run(show_items())
