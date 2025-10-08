"""Show items from the top super tender"""
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

        # Get the top tender ID
        top_tender = await conn.fetchrow("""
            SELECT tender_id, organization_name, total_homologated_value
            FROM analytics.super_tenders
            ORDER BY total_homologated_value DESC
            LIMIT 1
        """)

        print(f"🏆 TOP SUPER TENDER")
        print(f"{'='*100}")
        print(f"Organization: {top_tender['organization_name']}")
        print(f"Total Value: R${top_tender['total_homologated_value']:,.2f}")
        print(f"\n📦 THE 5 ITEMS:\n")

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
        """, top_tender['tender_id'])

        for item in items:
            print(f"Item #{item['item_number']}")
            print(f"   Description: {item['description']}")
            print(f"   Quantity: {item['quantity']} {item['unit'] if item['unit'] else ''}")
            print(f"   Unit Price: R${item['homologated_unit_value']:,.2f}")
            print(f"   TOTAL: R${item['homologated_total_value']:,.2f}")
            print(f"   Winner: {item['winner_name']}")
            print()

        await conn.close()
    finally:
        await connector.close_async()

asyncio.run(show_items())
