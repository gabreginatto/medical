#!/usr/bin/env python3
"""
Match tender items against Fernandes product list
"""

import asyncio
import json
import logging
from dotenv import load_dotenv

load_dotenv()

from database import create_db_manager_from_env, DatabaseOperations
from product_matcher import ProductMatcher

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def match_tender_items():
    """Match all tender items with Fernandes products"""

    print("=" * 70)
    print("🔍 MATCHING TENDER ITEMS WITH FERNANDES PRODUCTS")
    print("=" * 70)

    # Load Fernandes products
    print("\n1️⃣  Loading Fernandes products...")
    with open('fernandes_products.json', 'r', encoding='utf-8') as f:
        fernandes_products = json.load(f)
    print(f"   ✅ Loaded {len(fernandes_products)} Fernandes products")

    # Initialize
    db_manager = create_db_manager_from_env()
    db_ops = DatabaseOperations(db_manager)
    matcher = ProductMatcher()

    # Get all tender items with homologated prices
    print("\n2️⃣  Fetching tender items from database...")
    conn = await db_manager.get_connection()

    items = await conn.fetch("""
        SELECT
            ti.id,
            ti.description,
            ti.quantity,
            ti.homologated_unit_value,
            ti.homologated_total_value,
            ti.winner_name,
            t.control_number
        FROM tender_items ti
        JOIN tenders t ON ti.tender_id = t.id
        WHERE ti.homologated_unit_value IS NOT NULL
        ORDER BY ti.id
    """)

    await conn.close()

    print(f"   ✅ Found {len(items)} tender items with homologated prices")

    # Match each item
    print("\n3️⃣  Matching items...")
    matches_found = 0
    total_processed = 0

    usd_to_brl = 5.0  # Exchange rate

    for i, item in enumerate(items, 1):
        total_processed += 1

        # Use product matcher
        match_result = matcher.find_best_match(item['description'], fernandes_products, min_score=50.0)

        if match_result:
            product, score = match_result
            matches_found += 1

            # Calculate price comparison
            homologated_brl = float(item['homologated_unit_value'])
            fob_usd = float(product['FOB NINGBO USD/unit'])
            fob_brl = fob_usd * usd_to_brl

            price_diff_percent = ((homologated_brl - fob_brl) / homologated_brl * 100) if homologated_brl > 0 else 0
            is_competitive = price_diff_percent > 10  # At least 10% cheaper

            # Save to database
            match_data = {
                'tender_item_id': item['id'],
                'fernandes_product_code': product['CÓDIGO'],
                'fernandes_product_description': product['DESCRIÇÃO'],
                'match_score': score,
                'fob_price_usd': fob_usd,
                'moq': product['MOQ/unit'],
                'price_comparison_brl': homologated_brl,
                'price_comparison_usd': homologated_brl / usd_to_brl,
                'exchange_rate': usd_to_brl,
                'price_difference_percent': price_diff_percent,
                'is_competitive': is_competitive
            }

            # Insert into matched_products table
            await db_ops.insert_matched_product(match_data)

            if matches_found <= 5:  # Show first 5 matches
                print(f"\n   Match #{matches_found}:")
                print(f"   Tender Item: {item['description'][:60]}...")
                print(f"   Fernandes Product: {product['CÓDIGO']} - {product['DESCRIÇÃO'][:50]}...")
                print(f"   Match Score: {score:.1f}%")
                print(f"   Market Price: R$ {homologated_brl:.2f}")
                print(f"   Our FOB Price: R$ {fob_brl:.2f} (${fob_usd:.4f})")
                print(f"   Savings: {price_diff_percent:.1f}%")
                print(f"   Competitive: {'✅ Yes' if is_competitive else '❌ No'}")

        if i % 50 == 0:
            print(f"   Progress: {i}/{len(items)} items processed, {matches_found} matches found...")

    # Summary
    print("\n" + "=" * 70)
    print("📊 MATCHING SUMMARY")
    print("=" * 70)
    print(f"Total Items Processed: {total_processed}")
    print(f"Matches Found: {matches_found}")
    print(f"Match Rate: {matches_found / total_processed * 100:.1f}%")

    # Get competitive opportunities
    conn = await db_manager.get_connection()
    competitive_count = await conn.fetchval("""
        SELECT COUNT(*) FROM matched_products WHERE is_competitive = true
    """)
    await conn.close()

    print(f"Competitive Opportunities: {competitive_count}")

    print("\n✅ Matching complete!")

    await db_manager.close()

if __name__ == "__main__":
    asyncio.run(match_tender_items())
