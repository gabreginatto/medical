#!/usr/bin/env python3
"""Check RS state statistics in database"""

import asyncio
import os
from dotenv import load_dotenv
from src.database import create_db_manager_from_env

# Load environment variables
load_dotenv()

async def get_rs_stats():
    """Get tender and item counts for RS state"""
    db_manager = create_db_manager_from_env()
    conn = await db_manager.get_connection()

    try:
        # Count tenders from RS
        tender_count = await conn.fetchval(
            "SELECT COUNT(*) FROM tenders WHERE state_code = 'RS'"
        )

        # Count items from RS tenders
        item_count = await conn.fetchval("""
            SELECT COUNT(ti.*)
            FROM tender_items ti
            JOIN tenders t ON ti.tender_id = t.id
            WHERE t.state_code = 'RS'
        """)

        print(f"RS State Statistics:")
        print(f"  Tenders: {tender_count:,}")
        print(f"  Items: {item_count:,}")

    finally:
        await conn.close()
        await db_manager.close()

if __name__ == "__main__":
    asyncio.run(get_rs_stats())
