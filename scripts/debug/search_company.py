#!/usr/bin/env python3
"""
Search for a specific company in the database
"""
import os
import asyncio
from dotenv import load_dotenv
from database import create_db_manager_from_env

# Load environment variables
load_dotenv()

async def search_company(company_name: str):
    """Search for a company in tenders and tender items"""
    # Create database manager
    db_manager = create_db_manager_from_env()

    try:
        # Get connection
        conn = await db_manager.get_connection()

        print(f"Searching for company: {company_name}")
        print("=" * 80)

        # Search in tender_items (winner_name field)
        items = await conn.fetch("""
            SELECT
                ti.id,
                ti.winner_name,
                ti.winner_cnpj,
                ti.description,
                ti.quantity,
                ti.unit,
                ti.homologated_unit_value,
                ti.homologated_total_value,
                t.control_number,
                t.state_code,
                t.publication_date,
                o.name as buyer_name,
                t.modality_code
            FROM tender_items ti
            JOIN tenders t ON ti.tender_id = t.id
            LEFT JOIN organizations o ON t.organization_id = o.id
            WHERE ti.winner_name ILIKE $1
            ORDER BY t.publication_date DESC
        """, f"%{company_name}%")

        if items:
            print(f"\n✅ Found {len(items)} items won by companies matching '{company_name}':\n")

            total_value = 0
            for item in items:
                print(f"📋 Item ID: {item['id']}")
                print(f"   Winner: {item['winner_name']}")
                print(f"   CNPJ: {item['winner_cnpj'] or 'N/A'}")
                print(f"   Item: {item['description'][:100]}..." if len(item['description']) > 100 else f"   Item: {item['description']}")
                print(f"   Quantity: {item['quantity']} {item['unit'] or ''}")
                print(f"   Unit Value: R$ {item['homologated_unit_value']:,.2f}" if item['homologated_unit_value'] else "   Unit Value: N/A")
                print(f"   Total Value: R$ {item['homologated_total_value']:,.2f}" if item['homologated_total_value'] else "   Total Value: N/A")
                print(f"   Tender: {item['control_number']}")
                print(f"   State: {item['state_code']}")
                print(f"   Date: {item['publication_date']}")
                print(f"   Buyer: {item['buyer_name']}")
                print(f"   Modality Code: {item['modality_code']}")
                print()

                if item['homologated_total_value']:
                    total_value += item['homologated_total_value']

            print("=" * 80)
            print(f"💰 Total value of all items: R$ {total_value:,.2f}")
            print("=" * 80)
        else:
            print(f"\n❌ No items found for companies matching '{company_name}'")

        await conn.close()

    finally:
        await db_manager.close()

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python search_company.py 'Company Name'")
        sys.exit(1)

    company_name = sys.argv[1]
    asyncio.run(search_company(company_name))
