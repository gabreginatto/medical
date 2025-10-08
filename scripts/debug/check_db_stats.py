#!/usr/bin/env python3
"""
Quick script to check database statistics
"""
import os
import asyncio
from dotenv import load_dotenv
from database import create_db_manager_from_env

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

        await conn.close()

    finally:
        await db_manager.close()

if __name__ == "__main__":
    asyncio.run(check_stats())
