#!/usr/bin/env python3
"""
Search for a company by CNPJ in the database
"""
import os
import asyncio
from dotenv import load_dotenv
from src.database import create_db_manager_from_env

# Load environment variables
load_dotenv()

async def search_by_cnpj(cnpj: str):
    """Search for a company by CNPJ in tenders"""
    # Create database manager
    db_manager = create_db_manager_from_env()

    try:
        # Get connection
        conn = await db_manager.get_connection()

        # Clean CNPJ - remove dots, slashes, dashes
        cnpj_clean = cnpj.replace('.', '').replace('/', '').replace('-', '')

        print(f"Searching for CNPJ: {cnpj}")
        print(f"Cleaned CNPJ: {cnpj_clean}")
        print("=" * 80)

        # Search in tender_items (winner_cnpj field)
        # Try both formatted and clean versions
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
            WHERE REPLACE(REPLACE(REPLACE(ti.winner_cnpj, '.', ''), '/', ''), '-', '') = $1
            ORDER BY t.publication_date DESC
        """, cnpj_clean)

        if items:
            print(f"\n✅ Found {len(items)} items won by company with CNPJ {cnpj}:\n")

            # Get company name from first item
            company_name = items[0]['winner_name']
            print(f"🏢 Company: {company_name}")
            print(f"📋 CNPJ: {items[0]['winner_cnpj']}")
            print()

            # Calculate totals first
            total_value = 0
            for item in items:
                if item['homologated_total_value']:
                    total_value += item['homologated_total_value']

            # Get unique tenders count
            unique_tenders = len(set(item['control_number'] for item in items))

            # Get date range
            dates = [item['publication_date'] for item in items if item['publication_date']]
            min_date = min(dates) if dates else None
            max_date = max(dates) if dates else None

            # Get states
            states = set(item['state_code'] for item in items if item['state_code'])

            # Print summary stats
            print("=" * 80)
            print("SUMMARY STATISTICS")
            print("=" * 80)
            print(f"💰 Total value of all items: R$ {total_value:,.2f}")
            print(f"📊 Total items won: {len(items)}")
            print(f"📑 Unique tenders: {unique_tenders}")
            if min_date and max_date:
                print(f"📅 Date range: {min_date} to {max_date}")
            print(f"🗺️  States: {', '.join(sorted(states))}")
            print(f"💵 Average value per item: R$ {total_value / len(items):,.2f}")
            print("=" * 80)
            print()

            # If more than 20 items, show only first 10 and last 10
            if len(items) > 20:
                print(f"Showing first 10 and last 10 items (out of {len(items)} total):")
                print()
                items_to_show = list(items[:10]) + list(items[-10:])
                show_indices = list(range(1, 11)) + list(range(len(items)-9, len(items)+1))
            else:
                items_to_show = items
                show_indices = list(range(1, len(items)+1))

            for idx, item in zip(show_indices, items_to_show):
                if idx == len(items)-9 and len(items) > 20:
                    print("\n... [skipped middle items] ...\n")

                print(f"{'='*80}")
                print(f"Item #{idx} of {len(items)}")
                print(f"{'='*80}")
                print(f"   Item ID: {item['id']}")
                print(f"   Description: {item['description'][:150]}..." if len(item['description']) > 150 else f"   Description: {item['description']}")
                print(f"   Quantity: {item['quantity']} {item['unit'] or ''}")
                print(f"   Unit Value: R$ {item['homologated_unit_value']:,.2f}" if item['homologated_unit_value'] else "   Unit Value: N/A")
                print(f"   Total Value: R$ {item['homologated_total_value']:,.2f}" if item['homologated_total_value'] else "   Total Value: N/A")
                print(f"   Tender: {item['control_number']}")
                print(f"   State: {item['state_code']}")
                print(f"   Date: {item['publication_date']}")
                print(f"   Buyer: {item['buyer_name']}")
                print(f"   Modality Code: {item['modality_code']}")
                print()

            # Group by product category
            print("\n" + "=" * 80)
            print("TOP PRODUCT CATEGORIES (by total value)")
            print("=" * 80)

            from collections import defaultdict
            product_categories = defaultdict(lambda: {'count': 0, 'total_value': 0})

            for item in items:
                # Extract key words from description
                desc = item['description'].lower()
                category = 'Other'

                if 'cateter' in desc or 'picc' in desc:
                    category = 'Cateteres'
                elif 'sonda' in desc:
                    category = 'Sondas'
                elif 'aspira' in desc:
                    category = 'Sistemas de Aspiração'
                elif 'manta' in desc or 'termica' in desc:
                    category = 'Mantas Térmicas'
                elif 'equipo' in desc:
                    category = 'Equipos'
                elif 'filtro' in desc:
                    category = 'Filtros'
                elif 'mascara' in desc:
                    category = 'Máscaras'
                elif 'swab' in desc or 'higiene' in desc:
                    category = 'Higiene'
                elif 'extensor' in desc:
                    category = 'Extensores'

                product_categories[category]['count'] += 1
                if item['homologated_total_value']:
                    product_categories[category]['total_value'] += item['homologated_total_value']

            # Sort by total value
            sorted_categories = sorted(product_categories.items(), key=lambda x: x[1]['total_value'], reverse=True)

            for category, data in sorted_categories[:10]:
                print(f"{category:30s}: {data['count']:4d} items | R$ {data['total_value']:>15,.2f}")

            print("=" * 80)
        else:
            print(f"\n❌ No items found for CNPJ {cnpj}")
            print("\nTrying to find similar CNPJs...")

            # Try to find partial matches
            similar = await conn.fetch("""
                SELECT DISTINCT winner_cnpj, winner_name
                FROM tender_items
                WHERE winner_cnpj LIKE $1
                LIMIT 10
            """, f"%{cnpj_clean[:8]}%")

            if similar:
                print(f"\n🔍 Found {len(similar)} companies with similar CNPJ:")
                for s in similar:
                    print(f"   {s['winner_cnpj']} - {s['winner_name']}")
            else:
                print("\n❌ No similar CNPJs found")

        await conn.close()

    finally:
        await db_manager.close()

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python search_by_cnpj.py 'CNPJ'")
        print("Example: python search_by_cnpj.py '12.345.678/0001-90'")
        sys.exit(1)

    cnpj = sys.argv[1]
    asyncio.run(search_by_cnpj(cnpj))
