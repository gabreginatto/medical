#!/usr/bin/env python3
"""
Step 3: Create CSV comparison file for Excel
Formats AI matches into a CSV for price comparison between Fernandes and tender items
"""

import json
import csv
from pathlib import Path


def create_comparison_csv():
    """Create CSV file comparing Fernandes products with matched tender items"""

    # Load matches
    matches_file = 'data/ai_matches.json'
    print(f"📂 Loading matches from {matches_file}...")

    with open(matches_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
        matches = data['matches']

    print(f"✅ Loaded {len(matches)} matches")

    # Load Fernandes catalog for prices
    fernandes_file = 'config/fernandes_products.json'
    print(f"📂 Loading Fernandes catalog from {fernandes_file}...")

    with open(fernandes_file, 'r', encoding='utf-8') as f:
        fernandes_catalog = json.load(f)

    print(f"✅ Loaded {len(fernandes_catalog)} Fernandes products")

    # Create CSV
    output_file = 'data/price_comparison.csv'
    print(f"\n💾 Creating CSV file: {output_file}...")

    with open(output_file, 'w', newline='', encoding='utf-8-sig') as csvfile:
        writer = csv.writer(csvfile)

        # Write header
        writer.writerow([
            'Fernandes Product',
            'Fernandes Price (R$)',
            'Tender Item ID',
            'Tender Product Description',
            'Tender Unit Price (R$)',
            'Price Difference (R$)',
            'Price Difference (%)',
            'Confidence (%)',
            'Match Reasoning'
        ])

        # Sort matches by confidence (highest first)
        sorted_matches = sorted(matches, key=lambda x: x.get('confidence', 0), reverse=True)

        for match in sorted_matches:
            fernandes_index = match['fernandes_index']

            # Get Fernandes product (index is 1-based)
            fernandes_product = fernandes_catalog[fernandes_index - 1]
            fernandes_desc = match['fernandes_description']
            fernandes_price = fernandes_product.get('Price BRL', 0)

            # Get tender item details
            tender_id = match['tender_item_id']
            tender_desc = match.get('tender_item_description', '')
            tender_price = match.get('tender_item_price', 0)
            confidence = match.get('confidence', 0)
            reasoning = match.get('reasoning', '')

            # Calculate price difference
            price_diff = tender_price - fernandes_price

            # Calculate percentage difference (handle zero division)
            if fernandes_price > 0:
                price_diff_pct = (price_diff / fernandes_price) * 100
            else:
                price_diff_pct = 0

            writer.writerow([
                fernandes_desc,
                f"{fernandes_price:.2f}",
                tender_id,
                tender_desc,
                f"{tender_price:.2f}",
                f"{price_diff:.2f}",
                f"{price_diff_pct:.1f}%",
                f"{confidence}%",
                reasoning
            ])

    print(f"✅ Created CSV with {len(matches)} comparisons")

    # Print summary statistics
    print("\n" + "=" * 70)
    print("📊 PRICE COMPARISON SUMMARY")
    print("=" * 70)

    # Calculate statistics
    fernandes_wins = sum(1 for m in matches if m.get('tender_item_price', 0) > fernandes_catalog[m['fernandes_index']-1].get('Price BRL', 0))
    tender_wins = sum(1 for m in matches if m.get('tender_item_price', 0) < fernandes_catalog[m['fernandes_index']-1].get('Price BRL', 0))
    same_price = len(matches) - fernandes_wins - tender_wins

    print(f"Total Matches: {len(matches)}")
    print(f"Fernandes Price Lower: {fernandes_wins} ({(fernandes_wins/len(matches)*100):.1f}%)")
    print(f"Tender Price Lower: {tender_wins} ({(tender_wins/len(matches)*100):.1f}%)")
    print(f"Same Price: {same_price}")

    # Average prices
    avg_fernandes = sum(fernandes_catalog[m['fernandes_index']-1].get('Price BRL', 0) for m in matches) / len(matches)
    avg_tender = sum(m.get('tender_item_price', 0) for m in matches) / len(matches)

    print(f"\nAverage Fernandes Price: R$ {avg_fernandes:.2f}")
    print(f"Average Tender Price: R$ {avg_tender:.2f}")
    print(f"Average Difference: R$ {avg_tender - avg_fernandes:.2f}")

    print("\n" + "=" * 70)
    print(f"✅ CSV file ready for Excel: {output_file}")
    print("=" * 70)


if __name__ == "__main__":
    create_comparison_csv()
