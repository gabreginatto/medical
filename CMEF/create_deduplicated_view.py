#!/usr/bin/env python3
"""
Create deduplicated view of medical exhibitors
For duplicates, keep the record with the most complete information
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import create_db_manager_from_env


async def create_deduplicated_view():
    """Create deduplicated view of exhibitors"""

    print("=" * 70)
    print("CREATING DEDUPLICATED VIEW")
    print("=" * 70)
    print()

    db_manager = create_db_manager_from_env()
    db_manager.database_name = 'medical_exhibitors'
    conn = await db_manager.get_connection()

    try:
        # Step 1: Create a deduplication mapping table
        print("📋 Step 1: Creating deduplication mapping...")

        await conn.execute("DROP TABLE IF EXISTS exhibitor_dedup_map CASCADE")

        await conn.execute("""
            CREATE TABLE exhibitor_dedup_map AS
            WITH duplicates AS (
                -- Find all duplicate pairs based on exact English name match
                SELECT
                    c.id as cmef_id,
                    m.id as medica_id,
                    c.name as company_name,
                    -- Score each record based on completeness
                    (CASE WHEN c.company_name_zh IS NOT NULL THEN 1 ELSE 0 END +
                     CASE WHEN c.email IS NOT NULL THEN 1 ELSE 0 END +
                     CASE WHEN c.phone IS NOT NULL THEN 1 ELSE 0 END +
                     CASE WHEN c.website IS NOT NULL THEN 1 ELSE 0 END +
                     CASE WHEN c.address IS NOT NULL THEN 1 ELSE 0 END +
                     CASE WHEN c.company_description IS NOT NULL THEN 1 ELSE 0 END +
                     CASE WHEN c.booth_number IS NOT NULL THEN 1 ELSE 0 END) as cmef_score,
                    (CASE WHEN m.email IS NOT NULL THEN 1 ELSE 0 END +
                     CASE WHEN m.phone IS NOT NULL THEN 1 ELSE 0 END +
                     CASE WHEN m.website IS NOT NULL THEN 1 ELSE 0 END +
                     CASE WHEN m.address IS NOT NULL THEN 1 ELSE 0 END +
                     CASE WHEN m.company_description IS NOT NULL THEN 1 ELSE 0 END +
                     CASE WHEN m.location IS NOT NULL THEN 1 ELSE 0 END) as medica_score
                FROM medical_exhibitors c
                JOIN medical_exhibitors m ON LOWER(TRIM(c.name)) = LOWER(TRIM(m.name))
                WHERE c.data_source = 'CMEF'
                AND m.data_source = 'MEDICA'
            )
            SELECT
                cmef_id,
                medica_id,
                company_name,
                cmef_score,
                medica_score,
                -- Keep the record with higher completeness score
                CASE WHEN cmef_score >= medica_score THEN cmef_id ELSE medica_id END as keep_id,
                CASE WHEN cmef_score >= medica_score THEN medica_id ELSE cmef_id END as remove_id,
                CASE WHEN cmef_score >= medica_score THEN 'CMEF' ELSE 'MEDICA' END as kept_source
            FROM duplicates
        """)

        dup_count = await conn.fetchval("SELECT COUNT(*) FROM exhibitor_dedup_map")
        print(f"✅ Found {dup_count} duplicate pairs")
        print()

        # Show sample of what will be kept
        print("📊 Sample of deduplication decisions (first 10):")
        print("-" * 70)
        rows = await conn.fetch("""
            SELECT company_name, kept_source, cmef_score, medica_score
            FROM exhibitor_dedup_map
            ORDER BY company_name
            LIMIT 10
        """)

        for row in rows:
            print(f"  {row['company_name'][:50]:<50} -> Keep {row['kept_source']} "
                  f"(CMEF score: {row['cmef_score']}, MEDICA score: {row['medica_score']})")

        if dup_count > 10:
            print(f"  ... and {dup_count - 10} more")
        print()

        # Step 2: Create deduplicated view
        print("📋 Step 2: Creating deduplicated view...")

        await conn.execute("DROP VIEW IF EXISTS medical_exhibitors_unique CASCADE")

        await conn.execute("""
            CREATE VIEW medical_exhibitors_unique AS
            SELECT
                e.*,
                CASE
                    WHEN e.id IN (SELECT remove_id FROM exhibitor_dedup_map) THEN true
                    ELSE false
                END as is_duplicate_removed
            FROM medical_exhibitors e
            WHERE e.id NOT IN (SELECT remove_id FROM exhibitor_dedup_map)
        """)

        print("✅ Created view: medical_exhibitors_unique")
        print()

        # Step 3: Create merged duplicates view (optional - combines info from both records)
        print("📋 Step 3: Creating merged duplicates view...")

        await conn.execute("DROP VIEW IF EXISTS medical_exhibitors_merged_duplicates CASCADE")

        await conn.execute("""
            CREATE VIEW medical_exhibitors_merged_duplicates AS
            SELECT
                main.id,
                main.name,
                -- Prefer CMEF Chinese name if available
                COALESCE(main.company_name_zh, dup.company_name_zh) as company_name_zh,
                -- Combine location info
                CASE
                    WHEN main.location IS NOT NULL AND dup.location IS NOT NULL
                    THEN main.location || ' | ' || dup.location
                    ELSE COALESCE(main.location, dup.location)
                END as location,
                -- Combine booth info
                CASE
                    WHEN main.booth_number IS NOT NULL AND dup.location IS NOT NULL
                    THEN 'CMEF: ' || main.booth_number || ' | MEDICA: ' || dup.location
                    ELSE COALESCE(main.booth_number, dup.location)
                END as booth_info,
                -- Use best available for other fields
                COALESCE(main.email, dup.email) as email,
                COALESCE(main.phone, dup.phone) as phone,
                COALESCE(main.website, dup.website) as website,
                COALESCE(main.address, dup.address) as address,
                COALESCE(main.country, dup.country) as country,
                COALESCE(main.region, dup.region) as region,
                'BOTH (CMEF & MEDICA)' as events,
                main.data_source as primary_source,
                COALESCE(main.company_description, dup.company_description) as company_description,
                COALESCE(main.raw_text, dup.raw_text) as raw_text,
                COALESCE(main.product_category, dup.product_category) as product_category,
                COALESCE(main.product_keywords, dup.product_keywords) as product_keywords,
                COALESCE(main.category_confidence, dup.category_confidence) as category_confidence,
                COALESCE(main.website_validated, dup.website_validated) as website_validated,
                COALESCE(main.website_status_code, dup.website_status_code) as website_status_code,
                main.created_at,
                main.updated_at
            FROM medical_exhibitors main
            JOIN exhibitor_dedup_map m ON main.id = m.keep_id
            LEFT JOIN medical_exhibitors dup ON dup.id = m.remove_id
        """)

        print("✅ Created view: medical_exhibitors_merged_duplicates")
        print()

        # Step 4: Generate statistics
        print("=" * 70)
        print("DEDUPLICATION SUMMARY")
        print("=" * 70)
        print()

        total_original = await conn.fetchval("SELECT COUNT(*) FROM medical_exhibitors")
        total_unique = await conn.fetchval("SELECT COUNT(*) FROM medical_exhibitors_unique")
        total_removed = total_original - total_unique

        print(f"📊 Database Statistics:")
        print(f"  Original total: {total_original} companies")
        print(f"  Duplicates removed: {total_removed} companies")
        print(f"  Unique companies: {total_unique} companies")
        print(f"  Deduplication rate: {(total_removed / total_original * 100):.1f}%")
        print()

        # By source after dedup
        rows = await conn.fetch("""
            SELECT
                data_source,
                COUNT(*) as count
            FROM medical_exhibitors_unique
            GROUP BY data_source
            ORDER BY data_source
        """)

        print(f"📊 Unique Companies by Source:")
        for row in rows:
            print(f"  {row['data_source']}: {row['count']} companies")
        print()

        # Companies in both events
        both_count = await conn.fetchval("""
            SELECT COUNT(*) FROM medical_exhibitors_merged_duplicates
        """)

        print(f"🌍 International Companies (exhibiting at both CMEF & MEDICA): {both_count}")
        print()

        print("=" * 70)
        print("✅ DEDUPLICATION COMPLETED!")
        print("=" * 70)
        print()
        print("Available views:")
        print("  1. medical_exhibitors - Original data (all records)")
        print("  2. medical_exhibitors_unique - Deduplicated (one record per company)")
        print("  3. medical_exhibitors_merged_duplicates - Merged data for companies in both events")
        print()
        print("Example queries:")
        print("  SELECT * FROM medical_exhibitors_unique LIMIT 10;")
        print("  SELECT * FROM medical_exhibitors_merged_duplicates LIMIT 10;")
        print()

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(create_deduplicated_view())
