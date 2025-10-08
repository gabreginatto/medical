"""Export super tenders with items to CSV"""
import asyncio
import csv
from google.cloud.sql.connector import Connector

async def export_super_tenders():
    connector = Connector()

    try:
        conn = await connector.connect_async(
            "medical-473219:us-central1:pncp-medical-db",
            "asyncpg",
            user="postgres",
            password="TempPass123!",
            db="pncp_medical_data"
        )

        print("Fetching super tenders with items...\n")

        # Query super tenders with their items
        query = """
        SELECT
            st.tender_id,
            st.control_number,
            st.organization_name,
            st.state_code,
            st.total_homologated_value as tender_total_value,
            st.item_count,
            st.avg_value_per_item as tender_avg_per_item,
            st.efficiency_score,
            st.publication_date,
            st.tender_year,

            -- Item details
            ti.item_number,
            ti.description as item_description,
            ti.quantity,
            ti.unit,
            ti.homologated_unit_value as item_unit_price,
            ti.homologated_total_value as item_total_value,
            ti.winner_name,
            ti.winner_cnpj

        FROM analytics.super_tenders st
        LEFT JOIN tender_items ti ON st.tender_id = ti.tender_id
        ORDER BY st.total_homologated_value DESC, st.tender_id, ti.item_number
        """

        results = await conn.fetch(query)

        print(f"Found {len(results)} item records across super tenders")

        # Export to CSV
        csv_file = "/Users/gabrielreginatto/Desktop/Code/Medical/super_tenders_export.csv"

        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)

            # Header
            writer.writerow([
                'Tender ID',
                'Control Number',
                'Organization Name',
                'State',
                'Tender Total Value (R$)',
                'Total Items Count',
                'Avg Value per Item (R$)',
                'Efficiency Score',
                'Publication Date',
                'Year',
                'Item Number',
                'Item Description',
                'Quantity',
                'Unit',
                'Item Unit Price (R$)',
                'Item Total Value (R$)',
                'Winner Name',
                'Winner CNPJ'
            ])

            # Data rows
            for row in results:
                writer.writerow([
                    row['tender_id'],
                    row['control_number'],
                    row['organization_name'],
                    row['state_code'],
                    f"{row['tender_total_value']:.2f}" if row['tender_total_value'] else '',
                    row['item_count'],
                    f"{row['tender_avg_per_item']:.2f}" if row['tender_avg_per_item'] else '',
                    row['efficiency_score'],
                    row['publication_date'],
                    row['tender_year'],
                    row['item_number'] if row['item_number'] else '',
                    row['item_description'] if row['item_description'] else '',
                    row['quantity'] if row['quantity'] else '',
                    row['unit'] if row['unit'] else '',
                    f"{row['item_unit_price']:.2f}" if row['item_unit_price'] else '',
                    f"{row['item_total_value']:.2f}" if row['item_total_value'] else '',
                    row['winner_name'] if row['winner_name'] else '',
                    row['winner_cnpj'] if row['winner_cnpj'] else ''
                ])

        print(f"\n✅ CSV exported successfully!")
        print(f"📁 File location: {csv_file}")

        # Show summary
        print("\n📊 Summary:")
        summary = await conn.fetch("""
            SELECT
                COUNT(DISTINCT st.tender_id) as total_tenders,
                SUM(st.total_homologated_value) as total_value,
                COUNT(ti.id) as total_items
            FROM analytics.super_tenders st
            LEFT JOIN tender_items ti ON st.tender_id = ti.tender_id
        """)

        print(f"   Total Super Tenders: {summary[0]['total_tenders']}")
        print(f"   Total Value: R${summary[0]['total_value']:,.2f}")
        print(f"   Total Items: {summary[0]['total_items']}")

        # Show top 5
        print("\n🏆 Top 5 Super Tenders:")
        top5 = await conn.fetch("""
            SELECT
                organization_name,
                state_code,
                total_homologated_value,
                item_count
            FROM analytics.super_tenders
            ORDER BY total_homologated_value DESC
            LIMIT 5
        """)

        for i, row in enumerate(top5, 1):
            print(f"   {i}. {row['organization_name'][:50]} ({row['state_code']})")
            print(f"      R${row['total_homologated_value']:,.2f} | {row['item_count']} items")

        await conn.close()
    finally:
        await connector.close_async()

asyncio.run(export_super_tenders())
