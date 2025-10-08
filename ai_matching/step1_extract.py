#!/usr/bin/env python3
"""
Step 1: Extract filtered tender items from database
Filters items containing 'curativo' or 'transparente' keywords
"""

import asyncio
import json
from datetime import datetime
from dotenv import load_dotenv
from database import create_db_manager_from_env

load_dotenv()


async def extract_filtered_items():
    """Extract tender items with curativo or transparente keywords"""

    db_manager = create_db_manager_from_env()

    try:
        conn = await db_manager.get_connection()

        print("=" * 70)
        print("📊 EXTRACTING FILTERED TENDER ITEMS FOR AI MATCHING")
        print("=" * 70)

        # Query items with target keywords
        query = """
            SELECT
                ti.id,
                ti.description,
                ti.quantity,
                ti.unit,
                ti.homologated_unit_value,
                ti.tender_id,
                t.control_number,
                t.state_code,
                t.publication_date,
                o.name as organization_name,
                o.cnpj
            FROM tender_items ti
            JOIN tenders t ON ti.tender_id = t.id
            JOIN organizations o ON t.organization_id = o.id
            WHERE
                LOWER(ti.description) LIKE '%curativo%'
                OR LOWER(ti.description) LIKE '%transparente%'
            ORDER BY ti.homologated_unit_value DESC
        """

        print("\n🔍 Querying database...")
        items = await conn.fetch(query)

        print(f"✅ Found {len(items)} items matching filters")

        # Convert to list of dicts
        filtered_items = []
        for item in items:
            filtered_items.append({
                'id': item['id'],
                'description': item['description'],
                'quantity': float(item['quantity']) if item['quantity'] else 0,
                'unit': item['unit'],
                'homologated_unit_value': float(item['homologated_unit_value']) if item['homologated_unit_value'] else 0,
                'tender_id': item['tender_id'],
                'control_number': item['control_number'],
                'state_code': item['state_code'],
                'publication_date': item['publication_date'].isoformat() if item['publication_date'] else None,
                'organization_name': item['organization_name'],
                'cnpj': item['cnpj']
            })

        # Save to JSON file
        output_file = 'data/filtered_items_for_matching.json'
        print(f"\n💾 Saving to {output_file}...")

        import os
        os.makedirs('data', exist_ok=True)

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                'extracted_at': datetime.now().isoformat(),
                'total_items': len(filtered_items),
                'filters_applied': ['curativo', 'transparente'],
                'items': filtered_items
            }, f, indent=2, ensure_ascii=False)

        print(f"✅ Saved {len(filtered_items)} items to {output_file}")

        # Statistics
        print("\n" + "=" * 70)
        print("📊 EXTRACTION STATISTICS")
        print("=" * 70)

        total_value = sum(item['homologated_unit_value'] * item['quantity'] for item in filtered_items)
        avg_unit_value = sum(item['homologated_unit_value'] for item in filtered_items) / len(filtered_items) if filtered_items else 0

        print(f"Total Items: {len(filtered_items):,}")
        print(f"Total Value: R$ {total_value:,.2f}")
        print(f"Avg Unit Value: R$ {avg_unit_value:.2f}")

        # Top 10 most expensive items
        print("\n🔝 Top 10 Most Expensive Items:")
        sorted_items = sorted(filtered_items, key=lambda x: x['homologated_unit_value'], reverse=True)[:10]
        for i, item in enumerate(sorted_items, 1):
            print(f"{i}. R$ {item['homologated_unit_value']:.2f} - {item['description'][:60]}")

        # Keyword breakdown
        print("\n📋 Keyword Breakdown:")
        curativo_count = sum(1 for item in filtered_items if 'curativo' in item['description'].lower())
        transparente_count = sum(1 for item in filtered_items if 'transparente' in item['description'].lower())
        both_count = sum(1 for item in filtered_items if 'curativo' in item['description'].lower() and 'transparente' in item['description'].lower())

        print(f"Contains 'curativo': {curativo_count:,}")
        print(f"Contains 'transparente': {transparente_count:,}")
        print(f"Contains both: {both_count:,}")

        await conn.close()

        print("\n" + "=" * 70)
        print("✅ EXTRACTION COMPLETE")
        print("=" * 70)
        print(f"\n📁 Next step: Run ai_matching_step2_gemini.py")

        return filtered_items

    finally:
        await db_manager.close()


if __name__ == "__main__":
    asyncio.run(extract_filtered_items())
