#!/usr/bin/env python3
"""
Match tender items against Fernandes product list
"""

import asyncio
import json
import logging
from dotenv import load_dotenv

load_dotenv()

from .database import create_db_manager_from_env, DatabaseOperations
from .product_matcher import ProductMatcher

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def match_tender_items():
    """Match all tender items with Fernandes products"""

    from datetime import datetime
    start_time = datetime.now()

    logger.info("=" * 70)
    logger.info("🔍 MATCHING TENDER ITEMS WITH FERNANDES PRODUCTS")
    logger.info("=" * 70)

    # Load Fernandes products
    logger.info("")
    logger.info("1️⃣  Loading Fernandes products...")
    with open('config/fernandes_products.json', 'r', encoding='utf-8') as f:
        fernandes_products = json.load(f)
    logger.info(f"✅ Loaded {len(fernandes_products)} Fernandes products")

    # Initialize
    db_manager = create_db_manager_from_env()
    db_ops = DatabaseOperations(db_manager)
    matcher = ProductMatcher()

    # Get all tender items with homologated prices
    logger.info("")
    logger.info("2️⃣  Fetching tender items from database...")
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

    logger.info(f"✅ Found {len(items)} tender items with homologated prices")

    if len(items) == 0:
        logger.info("No items to match. Exiting.")
        await db_manager.close()
        return

    # Match each item
    logger.info("")
    logger.info("3️⃣  Matching items...")
    matches_found = 0
    total_processed = 0
    match_start = datetime.now()

    for i, item in enumerate(items, 1):
        total_processed += 1

        # Use product matcher
        match_result = matcher.find_best_match(item['description'], fernandes_products, min_score=50.0)

        if match_result:
            product, score = match_result
            matches_found += 1

            # Calculate price comparison (both prices now in BRL)
            homologated_brl = float(item['homologated_unit_value'])
            fob_brl = float(product['Price BRL'])

            price_diff_percent = ((homologated_brl - fob_brl) / homologated_brl * 100) if homologated_brl > 0 else 0

            # Save to database
            match_data = {
                'tender_item_id': item['id'],
                'fernandes_product_code': product['CÓDIGO'],
                'fernandes_product_description': product['DESCRIÇÃO'],
                'match_score': score,
                'fob_price_usd': None,  # No longer using USD prices
                'moq': product['MOQ/unit'],
                'price_comparison_brl': homologated_brl,
                'price_comparison_usd': None,  # No longer using USD prices
                'exchange_rate': None,  # No longer needed
                'price_difference_percent': price_diff_percent
            }

            # Insert into matched_products table
            await db_ops.insert_matched_product(match_data)

            if matches_found <= 5:  # Show first 5 matches
                logger.info(f"")
                logger.info(f"Match #{matches_found}:")
                logger.info(f"  Tender Item: {item['description'][:60]}...")
                logger.info(f"  Fernandes Product: {product['CÓDIGO']} - {product['DESCRIÇÃO'][:50]}...")
                logger.info(f"  Match Score: {score:.1f}%")
                logger.info(f"  Market Price: R$ {homologated_brl:.2f}")
                logger.info(f"  Our FOB Price: R$ {fob_brl:.2f}")
                logger.info(f"  Savings: {price_diff_percent:.1f}%")

        # Progress logging every 50 items
        if i % 50 == 0:
            elapsed = (datetime.now() - match_start).total_seconds()
            rate = i / elapsed if elapsed > 0 else 0
            remaining = len(items) - i
            eta = remaining / rate if rate > 0 else 0
            match_rate = (matches_found / i * 100) if i > 0 else 0

            logger.info(f"Progress: {i}/{len(items)} items ({i/len(items)*100:.1f}%) | "
                       f"Matches: {matches_found} ({match_rate:.1f}%) | "
                       f"Rate: {rate:.1f} items/sec | "
                       f"ETA: {eta/60:.1f} min")

    # Summary
    elapsed_total = (datetime.now() - start_time).total_seconds()
    logger.info("")
    logger.info("=" * 70)
    logger.info("📊 MATCHING SUMMARY")
    logger.info("=" * 70)
    logger.info(f"Total Items Processed: {total_processed}")
    logger.info(f"Matches Found: {matches_found}")
    if total_processed > 0:
        logger.info(f"Match Rate: {matches_found / total_processed * 100:.1f}%")
    logger.info(f"Total Time: {elapsed_total/60:.1f} minutes")
    logger.info(f"Average Rate: {total_processed/elapsed_total:.1f} items/sec")
    logger.info("")
    logger.info("✅ Matching complete!")

    await db_manager.close()

if __name__ == "__main__":
    asyncio.run(match_tender_items())
