#!/usr/bin/env python3
"""Delete tenders with NULL year or sequential_number"""

import asyncio
from dotenv import load_dotenv

load_dotenv()

from database import create_db_manager_from_env

async def delete_bad_tenders():
    db = create_db_manager_from_env()

    # Delete tenders with NULL year or sequential_number
    query = """
    DELETE FROM tenders
    WHERE year IS NULL OR sequential_number IS NULL
    RETURNING id, control_number;
    """

    conn = await db.get_connection()
    rows = await conn.fetch(query)
    await conn.close()

    print(f"Deleted {len(rows)} tenders with NULL year/sequential_number:")
    for row in rows:
        print(f"  - ID {row['id']}: {row['control_number']}")

    await db.close()
    return len(rows)

if __name__ == "__main__":
    deleted = asyncio.run(delete_bad_tenders())
    print(f"\n✅ Cleanup complete: {deleted} bad tenders removed")
