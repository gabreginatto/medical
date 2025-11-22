#!/usr/bin/env python3
import os
import asyncio
from dotenv import load_dotenv
from src.database import create_db_manager_from_env

load_dotenv()

async def check_dates():
    db_manager = create_db_manager_from_env()
    try:
        conn = await db_manager.get_connection()

        # Count by month
        result = await conn.fetch("""
            SELECT
                DATE_TRUNC('month', publication_date) as month,
                COUNT(*) as count
            FROM tenders
            GROUP BY month
            ORDER BY month DESC
            LIMIT 12
        """)

        print("\nTender counts by month:")
        for row in result:
            print(f"  {row['month'].strftime('%Y-%m')}: {row['count']:,} tenders")

        await conn.close()
    finally:
        await db_manager.close()

asyncio.run(check_dates())
