#!/usr/bin/env python3
"""
Find duplicate companies between CMEF and MEDICA datasets
Checks both English names and Chinese names
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import create_db_manager_from_env


async def find_duplicates():
    """Find duplicate companies between CMEF and MEDICA"""

    print("=" * 70)
    print("FINDING DUPLICATES BETWEEN CMEF AND MEDICA")
    print("=" * 70)
    print()

    db_manager = create_db_manager_from_env()
    db_manager.database_name = 'medical_exhibitors'
    conn = await db_manager.get_connection()

    try:
        # Method 1: Exact match on English name (case-insensitive)
        print("🔍 Method 1: Exact English name matches (case-insensitive)")
        print("-" * 70)

        rows = await conn.fetch("""
            SELECT
                c.name as cmef_name,
                c.company_name_zh as cmef_chinese,
                c.booth_number as cmef_booth,
                m.name as medica_name,
                m.location as medica_location,
                c.id as cmef_id,
                m.id as medica_id
            FROM medical_exhibitors c
            JOIN medical_exhibitors m ON LOWER(TRIM(c.name)) = LOWER(TRIM(m.name))
            WHERE c.data_source = 'CMEF'
            AND m.data_source = 'MEDICA'
            ORDER BY c.name
        """)

        print(f"Found {len(rows)} exact English name matches\n")

        if rows:
            for i, row in enumerate(rows[:20], 1):  # Show first 20
                print(f"{i}. {row['cmef_name']}")
                if row['cmef_chinese']:
                    print(f"   CMEF Chinese: {row['cmef_chinese']}")
                print(f"   CMEF Booth: {row['cmef_booth']}")
                print(f"   MEDICA Location: {row['medica_location']}")
                print(f"   IDs: CMEF={row['cmef_id']}, MEDICA={row['medica_id']}")
                print()

            if len(rows) > 20:
                print(f"... and {len(rows) - 20} more\n")

        # Method 2: Exact match on Chinese name (for companies with Chinese names)
        print("\n🔍 Method 2: Exact Chinese name matches")
        print("-" * 70)

        rows = await conn.fetch("""
            SELECT
                c.name as cmef_name,
                c.company_name_zh as chinese_name,
                c.booth_number as cmef_booth,
                m.name as medica_name,
                m.location as medica_location,
                c.id as cmef_id,
                m.id as medica_id
            FROM medical_exhibitors c
            JOIN medical_exhibitors m ON c.company_name_zh IS NOT NULL
                AND m.name IS NOT NULL
                AND TRIM(c.company_name_zh) = TRIM(m.name)
            WHERE c.data_source = 'CMEF'
            AND m.data_source = 'MEDICA'
            ORDER BY c.company_name_zh
        """)

        print(f"Found {len(rows)} Chinese name matches\n")

        if rows:
            for i, row in enumerate(rows[:20], 1):
                print(f"{i}. Chinese: {row['chinese_name']}")
                print(f"   CMEF English: {row['cmef_name']}")
                print(f"   MEDICA Name: {row['medica_name']}")
                print(f"   CMEF Booth: {row['cmef_booth']}")
                print(f"   MEDICA Location: {row['medica_location']}")
                print(f"   IDs: CMEF={row['cmef_id']}, MEDICA={row['medica_id']}")
                print()

            if len(rows) > 20:
                print(f"... and {len(rows) - 20} more\n")

        # Method 3: Fuzzy matching - companies with very similar names
        print("\n🔍 Method 3: Similar English names (substring matches)")
        print("-" * 70)
        print("(Checking if MEDICA name contains CMEF name or vice versa, min 10 chars)")
        print()

        rows = await conn.fetch("""
            SELECT
                c.name as cmef_name,
                c.company_name_zh as cmef_chinese,
                c.booth_number as cmef_booth,
                m.name as medica_name,
                m.location as medica_location,
                c.id as cmef_id,
                m.id as medica_id,
                CASE
                    WHEN LENGTH(c.name) < LENGTH(m.name) THEN LENGTH(c.name)
                    ELSE LENGTH(m.name)
                END as min_length
            FROM medical_exhibitors c
            CROSS JOIN medical_exhibitors m
            WHERE c.data_source = 'CMEF'
            AND m.data_source = 'MEDICA'
            AND c.name != m.name  -- Exclude exact matches (already found above)
            AND (
                (LENGTH(c.name) >= 10 AND LOWER(m.name) LIKE '%' || LOWER(c.name) || '%')
                OR (LENGTH(m.name) >= 10 AND LOWER(c.name) LIKE '%' || LOWER(m.name) || '%')
            )
            ORDER BY min_length DESC
            LIMIT 50
        """)

        print(f"Found {len(rows)} similar name matches\n")

        if rows:
            for i, row in enumerate(rows[:20], 1):
                print(f"{i}. CMEF: {row['cmef_name']}")
                print(f"   MEDICA: {row['medica_name']}")
                if row['cmef_chinese']:
                    print(f"   CMEF Chinese: {row['cmef_chinese']}")
                print(f"   CMEF Booth: {row['cmef_booth']}")
                print(f"   MEDICA Location: {row['medica_location']}")
                print(f"   IDs: CMEF={row['cmef_id']}, MEDICA={row['medica_id']}")
                print()

            if len(rows) > 20:
                print(f"... and {len(rows) - 20} more\n")

        # Summary statistics
        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)

        # Total exact duplicates
        exact_english = await conn.fetchval("""
            SELECT COUNT(*)
            FROM medical_exhibitors c
            JOIN medical_exhibitors m ON LOWER(TRIM(c.name)) = LOWER(TRIM(m.name))
            WHERE c.data_source = 'CMEF' AND m.data_source = 'MEDICA'
        """)

        exact_chinese = await conn.fetchval("""
            SELECT COUNT(*)
            FROM medical_exhibitors c
            JOIN medical_exhibitors m ON c.company_name_zh IS NOT NULL
                AND m.name IS NOT NULL
                AND TRIM(c.company_name_zh) = TRIM(m.name)
            WHERE c.data_source = 'CMEF' AND m.data_source = 'MEDICA'
        """)

        print(f"\n📊 Duplicate Statistics:")
        print(f"  Exact English name matches: {exact_english}")
        print(f"  Exact Chinese name matches: {exact_chinese}")
        print(f"  Similar name matches (potential): {len(rows)}")
        print()
        print(f"💡 Recommendation:")
        if exact_english > 0 or exact_chinese > 0:
            total_exact = exact_english + exact_chinese
            print(f"  Found {total_exact} exact duplicates that should likely be merged")
            print(f"  This represents {total_exact / 57.17:.1f}% of the total database")
        else:
            print("  No exact duplicates found - data appears clean!")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(find_duplicates())
