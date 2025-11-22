#!/usr/bin/env python3
"""
Step 3: Save AI matching results to database
Saves high-confidence matches to matched_products table
Exports medium-confidence matches to CSV for review
"""

import asyncio
import json
import csv
import os
from datetime import datetime
from dotenv import load_dotenv
from src.database import create_db_manager_from_env

load_dotenv()


async def save_matches_to_database():
    """Save AI matching results to database"""

    print("=" * 70)
    print("💾 SAVING AI MATCHES TO DATABASE")
    print("=" * 70)

    # Load matches
    matches_file = 'data/ai_matches.json'

    if not os.path.exists(matches_file):
        print(f"❌ Error: {matches_file} not found!")
        print("   Run ai_matching_step2_gemini.py first")
        return

    print(f"\n📂 Loading matches from {matches_file}...")

    with open(matches_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    all_matches = data['matches']
    high_confidence = data['tiers']['high_confidence']
    medium_confidence = data['tiers']['medium_confidence']

    print(f"✅ Loaded {len(all_matches)} total matches")
    print(f"   - High confidence (≥90%): {len(high_confidence)}")
    print(f"   - Medium confidence (70-89%): {len(medium_confidence)}")

    db_manager = create_db_manager_from_env()

    try:
        conn = await db_manager.get_connection()

        # Save high-confidence matches to database
        print("\n💾 Saving high-confidence matches to database...")

        saved_count = 0
        skipped_count = 0
        error_count = 0

        for match in high_confidence:
            try:
                tender_item_id = match['tender_item_id']
                fernandes_code = match['fernandes_code']
                confidence = match['confidence']
                reasoning = match.get('reasoning', '')

                # Check if this tender_item already has a match
                existing = await conn.fetchval(
                    "SELECT COUNT(*) FROM matched_products WHERE tender_item_id = $1",
                    tender_item_id
                )

                if existing > 0:
                    skipped_count += 1
                    continue

                # Get Fernandes product details
                # NOTE: Adjust this based on your actual fernandes_products table structure
                fernandes_product = await conn.fetchrow(
                    "SELECT id, price FROM fernandes_products WHERE code = $1",
                    fernandes_code
                )

                if not fernandes_product:
                    # If product not in DB, skip for now
                    # Could also insert it here
                    skipped_count += 1
                    continue

                fernandes_product_id = fernandes_product['id']
                fernandes_price = fernandes_product['price']

                # Get tender item details for price comparison
                tender_item = await conn.fetchrow(
                    "SELECT homologated_unit_value FROM tender_items WHERE id = $1",
                    tender_item_id
                )

                if not tender_item:
                    skipped_count += 1
                    continue

                tender_price = float(tender_item['homologated_unit_value'])

                # Calculate price difference
                if fernandes_price > 0:
                    price_diff_percent = ((tender_price - fernandes_price) / fernandes_price) * 100
                else:
                    price_diff_percent = 0

                # Insert match
                await conn.execute("""
                    INSERT INTO matched_products (
                        tender_item_id,
                        fernandes_product_id,
                        match_confidence,
                        match_method,
                        match_reasoning,
                        price_difference_percent,
                        created_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                """, tender_item_id, fernandes_product_id, confidence,
                     'ai_gemini', reasoning, price_diff_percent, datetime.now())

                saved_count += 1

            except Exception as e:
                print(f"❌ Error saving match for item {match.get('tender_item_id')}: {e}")
                error_count += 1

        print(f"✅ Saved {saved_count} high-confidence matches to database")
        print(f"   - Skipped (already matched or missing data): {skipped_count}")
        print(f"   - Errors: {error_count}")

        # Export medium-confidence matches to CSV for review
        if medium_confidence:
            print("\n📤 Exporting medium-confidence matches to CSV for review...")

            csv_file = 'data/medium_confidence_matches_for_review.csv'

            # Get full item details for CSV
            medium_details = []
            for match in medium_confidence:
                item = await conn.fetchrow("""
                    SELECT
                        ti.id,
                        ti.description,
                        ti.homologated_unit_value,
                        ti.quantity,
                        t.control_number,
                        o.name as organization_name
                    FROM tender_items ti
                    JOIN tenders t ON ti.tender_id = t.id
                    JOIN organizations o ON t.organization_id = o.id
                    WHERE ti.id = $1
                """, match['tender_item_id'])

                if item:
                    medium_details.append({
                        'tender_item_id': item['id'],
                        'description': item['description'],
                        'tender_price': float(item['homologated_unit_value']),
                        'quantity': float(item['quantity']),
                        'control_number': item['control_number'],
                        'organization': item['organization_name'],
                        'matched_fernandes_code': match['fernandes_code'],
                        'matched_fernandes_name': match['fernandes_name'],
                        'confidence': match['confidence'],
                        'reasoning': match.get('reasoning', ''),
                        'accept': '',  # For manual review
                        'notes': ''    # For manual notes
                    })

            # Write CSV
            if medium_details:
                with open(csv_file, 'w', newline='', encoding='utf-8') as f:
                    fieldnames = [
                        'tender_item_id', 'description', 'tender_price', 'quantity',
                        'control_number', 'organization', 'matched_fernandes_code',
                        'matched_fernandes_name', 'confidence', 'reasoning',
                        'accept', 'notes'
                    ]
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(medium_details)

                print(f"✅ Exported {len(medium_details)} matches to {csv_file}")
                print(f"   Review this file and mark 'accept' column with YES/NO")

        await conn.close()

        print("\n" + "=" * 70)
        print("📊 SAVE SUMMARY")
        print("=" * 70)
        print(f"High Confidence Saved: {saved_count}")
        print(f"Medium Confidence (CSV): {len(medium_confidence)}")
        print(f"Total Processed: {saved_count + len(medium_confidence)}")
        print("=" * 70)
        print("\n✅ SAVE COMPLETE")
        print("\n📁 Next step: Run ai_matching_step4_report.py for detailed report")

    finally:
        await db_manager.close()


if __name__ == "__main__":
    asyncio.run(save_matches_to_database())
