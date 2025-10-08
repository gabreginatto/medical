#!/usr/bin/env python3
"""
Step 4: Generate comprehensive matching report
Analyzes AI matching results and provides insights
"""

import asyncio
import json
import os
from datetime import datetime
from dotenv import load_dotenv
from database import create_db_manager_from_env

load_dotenv()


async def generate_matching_report():
    """Generate comprehensive matching report"""

    print("=" * 70)
    print("📊 AI MATCHING RESULTS REPORT")
    print("=" * 70)

    # Load original filtered items
    items_file = 'data/filtered_items_for_matching.json'
    matches_file = 'data/ai_matches.json'

    if not os.path.exists(items_file) or not os.path.exists(matches_file):
        print("❌ Required files not found!")
        return

    with open(items_file, 'r', encoding='utf-8') as f:
        items_data = json.load(f)
        total_items = len(items_data['items'])

    with open(matches_file, 'r', encoding='utf-8') as f:
        matches_data = json.load(f)
        all_matches = matches_data['matches']
        high_conf = matches_data['tiers']['high_confidence']
        medium_conf = matches_data['tiers']['medium_confidence']

    # Database stats
    db_manager = create_db_manager_from_env()

    try:
        conn = await db_manager.get_connection()

        # Count saved matches
        saved_count = await conn.fetchval(
            "SELECT COUNT(*) FROM matched_products WHERE match_method = 'ai_gemini'"
        )

        # Get price comparison stats
        price_stats = await conn.fetchrow("""
            SELECT
                AVG(price_difference_percent) as avg_price_diff,
                MIN(price_difference_percent) as min_price_diff,
                MAX(price_difference_percent) as max_price_diff,
                COUNT(*) FILTER (WHERE price_difference_percent < 0) as cheaper_count,
                COUNT(*) FILTER (WHERE price_difference_percent > 0) as expensive_count
            FROM matched_products
            WHERE match_method = 'ai_gemini'
        """)

        # Get top opportunities (biggest price differences)
        top_opportunities = await conn.fetch("""
            SELECT
                ti.description,
                ti.homologated_unit_value as tender_price,
                fp.price as fernandes_price,
                mp.price_difference_percent,
                ti.quantity,
                t.control_number,
                o.name as organization_name
            FROM matched_products mp
            JOIN tender_items ti ON mp.tender_item_id = ti.id
            JOIN fernandes_products fp ON mp.fernandes_product_id = fp.id
            JOIN tenders t ON ti.tender_id = t.id
            JOIN organizations o ON t.organization_id = o.id
            WHERE mp.match_method = 'ai_gemini'
            ORDER BY mp.price_difference_percent DESC
            LIMIT 10
        """)

        await conn.close()

        # Generate report
        print("\n" + "=" * 70)
        print("📈 MATCHING PERFORMANCE")
        print("=" * 70)

        match_rate = (len(all_matches) / total_items * 100) if total_items > 0 else 0
        high_conf_rate = (len(high_conf) / total_items * 100) if total_items > 0 else 0

        print(f"Total Items Filtered: {total_items:,}")
        print(f"Total Matches Found: {len(all_matches):,}")
        print(f"Match Rate: {match_rate:.1f}%")
        print(f"\nConfidence Distribution:")
        print(f"  High (≥90%): {len(high_conf):,} ({len(high_conf)/len(all_matches)*100:.1f}%)")
        print(f"  Medium (70-89%): {len(medium_conf):,} ({len(medium_conf)/len(all_matches)*100:.1f}%)")

        if all_matches:
            avg_confidence = sum(m['confidence'] for m in all_matches) / len(all_matches)
            print(f"\nAverage Confidence: {avg_confidence:.1f}%")

        print(f"\nSaved to Database: {saved_count:,}")
        print(f"Pending Review (CSV): {len(medium_conf):,}")

        # Price analysis
        if price_stats and price_stats['avg_price_diff'] is not None:
            print("\n" + "=" * 70)
            print("💰 PRICE COMPARISON ANALYSIS")
            print("=" * 70)

            avg_diff = float(price_stats['avg_price_diff'])
            min_diff = float(price_stats['min_price_diff'])
            max_diff = float(price_stats['max_price_diff'])
            cheaper = price_stats['cheaper_count']
            expensive = price_stats['expensive_count']

            print(f"Average Price Difference: {avg_diff:+.1f}%")
            print(f"Range: {min_diff:+.1f}% to {max_diff:+.1f}%")
            print(f"\nTenders vs Fernandes:")
            print(f"  Cheaper than Fernandes: {cheaper} ({cheaper/(cheaper+expensive)*100:.1f}%)")
            print(f"  More expensive: {expensive} ({expensive/(cheaper+expensive)*100:.1f}%)")

        # Top opportunities
        if top_opportunities:
            print("\n" + "=" * 70)
            print("🎯 TOP 10 PRICE OPPORTUNITIES")
            print("=" * 70)
            print("(Highest price differences vs Fernandes catalog)")
            print()

            for i, opp in enumerate(top_opportunities, 1):
                tender_price = float(opp['tender_price'])
                fernandes_price = float(opp['fernandes_price'])
                diff_pct = float(opp['price_difference_percent'])
                qty = float(opp['quantity'])

                potential_savings = (tender_price - fernandes_price) * qty if diff_pct > 0 else 0

                print(f"{i}. {opp['description'][:50]}")
                print(f"   Tender: R$ {tender_price:.2f} | Fernandes: R$ {fernandes_price:.2f}")
                print(f"   Difference: {diff_pct:+.1f}% | Qty: {qty:.0f}")
                if potential_savings > 0:
                    print(f"   Potential savings: R$ {potential_savings:,.2f}")
                print(f"   Org: {opp['organization_name']}")
                print()

        # Summary statistics
        print("=" * 70)
        print("📋 SUMMARY")
        print("=" * 70)

        print(f"✅ Successfully matched: {len(high_conf):,} items ({high_conf_rate:.1f}% of total)")
        print(f"📋 Pending review: {len(medium_conf):,} items")
        print(f"❌ Unmatched: {total_items - len(all_matches):,} items")

        # Recommendations
        print("\n" + "=" * 70)
        print("💡 RECOMMENDATIONS")
        print("=" * 70)

        if len(high_conf) > 0:
            print(f"✅ {len(high_conf)} high-confidence matches saved to database")
            print("   → Ready for Notion export")

        if len(medium_conf) > 0:
            print(f"\n📋 {len(medium_conf)} medium-confidence matches exported to CSV")
            print("   → Review data/medium_confidence_matches_for_review.csv")
            print("   → Mark 'accept' column with YES for valid matches")

        unmatched = total_items - len(all_matches)
        if unmatched > 0:
            print(f"\n⚠️  {unmatched} items remain unmatched ({unmatched/total_items*100:.1f}%)")
            print("   → Consider expanding Fernandes catalog")
            print("   → Try different keyword filters")
            print("   → Adjust AI matching prompt")

        # Cost estimation (approximate)
        print("\n" + "=" * 70)
        print("💵 ESTIMATED COST")
        print("=" * 70)

        # Rough estimation based on typical token usage
        num_batches = (total_items + 49) // 50
        avg_tokens_per_batch = 10000  # Input + output
        total_tokens = num_batches * avg_tokens_per_batch
        estimated_cost = (total_tokens / 1_000_000) * 0.375  # Average of input/output cost

        print(f"API Calls: ~{num_batches}")
        print(f"Estimated Tokens: ~{total_tokens:,}")
        print(f"Estimated Cost: ~${estimated_cost:.3f}")

        print("\n" + "=" * 70)
        print("✅ REPORT COMPLETE")
        print("=" * 70)

    finally:
        await db_manager.close()


if __name__ == "__main__":
    asyncio.run(generate_matching_report())
