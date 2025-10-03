#!/usr/bin/env python3
"""
Add is_competitive column to matched_products table
"""

import asyncio
from dotenv import load_dotenv

load_dotenv()

from database import create_db_manager_from_env

async def add_column():
    """Add is_competitive column if it doesn't exist"""

    db_manager = create_db_manager_from_env()
    conn = await db_manager.get_connection()

    try:
        # Check if column exists
        result = await conn.fetchval("""
            SELECT COUNT(*)
            FROM information_schema.columns
            WHERE table_name = 'matched_products'
            AND column_name = 'is_competitive'
        """)

        if result == 0:
            print("Adding is_competitive column...")
            await conn.execute("""
                ALTER TABLE matched_products
                ADD COLUMN is_competitive BOOLEAN
            """)
            print("✅ Column added successfully")
        else:
            print("✅ Column already exists")

    finally:
        await conn.close()
        await db_manager.close()

if __name__ == "__main__":
    asyncio.run(add_column())
