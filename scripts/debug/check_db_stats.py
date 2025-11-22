#!/usr/bin/env python3
"""
Quick script to check database statistics
"""
import os
import asyncio
from dotenv import load_dotenv
from src.database import create_db_manager_from_env

# Load environment variables
load_dotenv()

async def check_stats():
    """Check database statistics"""
    # Create database manager
    db_manager = create_db_manager_from_env()

    try:
        # Get connection
        conn = await db_manager.get_connection()

        # Count tenders
        tender_count = await conn.fetchval("SELECT COUNT(*) FROM tenders")
        print(f"Total tenders: {tender_count:,}")

        # Count tender items
        item_count = await conn.fetchval("SELECT COUNT(*) FROM tender_items")
        print(f"Total tender items: {item_count:,}")

        # Get most recent tender date
        latest_date = await conn.fetchval("""
            SELECT MAX(publication_date)
            FROM tenders
        """)

        if latest_date:
            print(f"\nMost recent tender date: {latest_date}")

        # Get tenders per month
        print("\n--- Tenders per month ---")
        tender_months = await conn.fetch("""
            SELECT
                DATE_TRUNC('month', publication_date) as month,
                COUNT(*) as count
            FROM tenders
            WHERE publication_date IS NOT NULL
            GROUP BY DATE_TRUNC('month', publication_date)
            ORDER BY month DESC
        """)

        for row in tender_months:
            print(f"{row['month'].strftime('%Y-%m')}: {row['count']:,} tenders")

        # Get items per month (based on tender publication date)
        print("\n--- Tender items per month ---")
        item_months = await conn.fetch("""
            SELECT
                DATE_TRUNC('month', t.publication_date) as month,
                COUNT(ti.id) as count
            FROM tender_items ti
            JOIN tenders t ON ti.tender_id = t.id
            WHERE t.publication_date IS NOT NULL
            GROUP BY DATE_TRUNC('month', t.publication_date)
            ORDER BY month DESC
        """)

        for row in item_months:
            print(f"{row['month'].strftime('%Y-%m')}: {row['count']:,} items")

        # Get states with tenders and their months
        print("\n--- Tenders by state and month ---")
        state_months = await conn.fetch("""
            SELECT
                state_code,
                DATE_TRUNC('month', publication_date) as month,
                COUNT(*) as count
            FROM tenders
            WHERE publication_date IS NOT NULL AND state_code IS NOT NULL
            GROUP BY state_code, DATE_TRUNC('month', publication_date)
            ORDER BY state_code, month DESC
        """)

        # Group by state
        states_data = {}
        for row in state_months:
            state = row['state_code']
            month = row['month'].strftime('%Y-%m')
            count = row['count']

            if state not in states_data:
                states_data[state] = []
            states_data[state].append((month, count))

        for state in sorted(states_data.keys()):
            print(f"\n{state}:")
            for month, count in states_data[state]:
                print(f"  {month}: {count:,} tenders")

        # Check for tenders with NULL state_code
        null_state_count = await conn.fetchval("""
            SELECT COUNT(*)
            FROM tenders
            WHERE state_code IS NULL
        """)
        if null_state_count > 0:
            print(f"\n⚠️  Warning: {null_state_count:,} tenders have NULL state_code")

        # Check for tenders without items
        print("\n--- Tenders without items ---")
        tenders_no_items = await conn.fetchval("""
            SELECT COUNT(*)
            FROM tenders t
            LEFT JOIN tender_items ti ON t.id = ti.tender_id
            WHERE ti.id IS NULL
        """)
        print(f"Tenders with no items: {tenders_no_items:,}")

        if tenders_no_items > 0:
            # Show some examples
            examples = await conn.fetch("""
                SELECT t.id, t.state_code, t.publication_date, t.pncp_id
                FROM tenders t
                LEFT JOIN tender_items ti ON t.id = ti.tender_id
                WHERE ti.id IS NULL
                LIMIT 10
            """)
            print("\nExamples of tenders without items:")
            for ex in examples:
                print(f"  ID: {ex['id']}, State: {ex['state_code']}, Date: {ex['publication_date']}, PNCP ID: {ex['pncp_id']}")

        await conn.close()

    finally:
        await db_manager.close()

if __name__ == "__main__":
    asyncio.run(check_stats())
