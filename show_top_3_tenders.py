"""Show items from the top 3 super tenders"""
import asyncio
from google.cloud.sql.connector import Connector

async def show_items():
    connector = Connector()

    try:
        conn = await connector.connect_async(
            "medical-473219:us-central1:pncp-medical-db",
            "asyncpg",
            user="postgres",
            password="TempPass123!",
            db="pncp_medical_data"
        )

        # Get top 3 tenders
        top_tenders = await conn.fetch("""
            SELECT tender_id, organization_name, state_code, total_homologated_value, item_count
            FROM analytics.super_tenders
            ORDER BY total_homologated_value DESC
            LIMIT 3
        """)

        for rank, tender in enumerate(top_tenders, 1):
            print(f"\n{'='*100}")
            print(f"🏆 SUPER TENDER #{rank}")
            print(f"{'='*100}")
            print(f"Organization: {tender['organization_name']}")
            print(f"State: {tender['state_code']}")
            print(f"Total Value: R${tender['total_homologated_value']:,.2f}")
            print(f"Item Count: {tender['item_count']}")
            print(f"\n📦 ITEMS:\n")

            # Get items for this tender
            items = await conn.fetch("""
                SELECT
                    item_number,
                    description,
                    quantity,
                    unit,
                    homologated_unit_value,
                    homologated_total_value,
                    winner_name
                FROM tender_items
                WHERE tender_id = $1
                ORDER BY item_number
            """, tender['tender_id'])

            for item in items:
                print(f"Item #{item['item_number']}")
                print(f"   Description: {item['description'][:100]}...")  # Truncate long descriptions
                if item['quantity']:
                    print(f"   Quantity: {item['quantity']:,.0f} {item['unit'] if item['unit'] else ''}")
                if item['homologated_unit_value']:
                    print(f"   Unit Price: R${item['homologated_unit_value']:,.2f}")
                if item['homologated_total_value']:
                    print(f"   TOTAL: R${item['homologated_total_value']:,.2f}")
                if item['winner_name']:
                    print(f"   Winner: {item['winner_name'][:60]}")
                print()

        await conn.close()
    finally:
        await connector.close_async()

asyncio.run(show_items())
