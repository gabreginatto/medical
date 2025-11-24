#!/usr/bin/env python3
"""
Automatic Unified Database Setup

Uses existing database connection infrastructure to automatically:
1. Create schema in medical_exhibitors database
2. Import CMEF data
3. Import MEDICA data
"""

import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import create_db_manager_from_env

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/auto_unified_setup.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


async def setup_unified_database():
    """Automatically setup unified database"""

    logger.info("=" * 70)
    logger.info("AUTOMATIC UNIFIED DATABASE SETUP")
    logger.info("=" * 70)

    # Connect using existing infrastructure
    logger.info("\n📡 Connecting to Cloud SQL...")
    db_manager = create_db_manager_from_env()

    # Override database name to medical_exhibitors
    db_manager.database_name = 'medical_exhibitors'

    logger.info(f"  Instance: {db_manager.connection_name}")
    logger.info(f"  Database: medical_exhibitors")

    conn = await db_manager.get_connection()

    try:
        # Step 1: Create Schema
        logger.info("\n" + "=" * 70)
        logger.info("STEP 1: CREATING SCHEMA")
        logger.info("=" * 70)

        # Drop existing table if it exists (to fix schema)
        await conn.execute("DROP TABLE IF EXISTS medical_exhibitors CASCADE")

        await conn.execute("""
            CREATE TABLE medical_exhibitors (
                id SERIAL PRIMARY KEY,
                name VARCHAR(500) NOT NULL,
                company_name_zh VARCHAR(500),
                location VARCHAR(200),
                booth_number VARCHAR(200),
                email VARCHAR(255),
                phone VARCHAR(100),
                website VARCHAR(500),
                address TEXT,
                country VARCHAR(100),
                region VARCHAR(100),
                event VARCHAR(100) NOT NULL,
                data_source VARCHAR(50) NOT NULL,
                company_description TEXT,
                raw_text TEXT,
                product_category VARCHAR(200),
                product_keywords TEXT[],
                category_confidence FLOAT,
                website_validated BOOLEAN DEFAULT FALSE,
                website_status_code INTEGER,
                scraped_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW(),
                CONSTRAINT unique_company_event UNIQUE(name, event)
            )
        """)
        logger.info("✅ Table created")

        # Create indexes
        logger.info("\n📑 Creating indexes...")
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_exhibitors_name ON medical_exhibitors(name)",
            "CREATE INDEX IF NOT EXISTS idx_exhibitors_data_source ON medical_exhibitors(data_source)",
            "CREATE INDEX IF NOT EXISTS idx_exhibitors_category ON medical_exhibitors(product_category)",
            "CREATE INDEX IF NOT EXISTS idx_exhibitors_booth ON medical_exhibitors(booth_number)",
            "CREATE INDEX IF NOT EXISTS idx_exhibitors_keywords ON medical_exhibitors USING GIN(product_keywords)",
        ]

        for idx_sql in indexes:
            await conn.execute(idx_sql)

        logger.info(f"✅ Created {len(indexes)} indexes")

        # Step 2: Import CMEF Data
        logger.info("\n" + "=" * 70)
        logger.info("STEP 2: IMPORTING CMEF DATA")
        logger.info("=" * 70)

        cmef_file = '/Users/gabrielreginatto/Desktop/Code/Medical/CMEF/data/enriched_companies.json'
        logger.info(f"📖 Loading: {cmef_file}")

        with open(cmef_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        companies = data.get('companies', [])
        logger.info(f"✅ Loaded {len(companies)} CMEF companies")

        insert_sql = """
            INSERT INTO medical_exhibitors (
                name, company_name_zh, location, booth_number,
                company_description, email, phone, website, address,
                country, region, event,
                product_category, product_keywords, category_confidence,
                website_validated, website_status_code,
                data_source, scraped_at
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, NOW()
            )
            ON CONFLICT (name, event) DO NOTHING
        """

        logger.info("💾 Inserting CMEF companies...")
        inserted = 0
        skipped = 0
        async with conn.transaction():
            for i, company in enumerate(companies, 1):
                # Skip companies without names
                if not company.get('company_name_en'):
                    skipped += 1
                    continue

                await conn.execute(insert_sql,
                    company.get('company_name_en'),
                    company.get('company_name_zh'),
                    company.get('booth_number'),
                    company.get('booth_number'),
                    company.get('scope_description'),
                    company.get('email'),
                    company.get('phone'),
                    company.get('website'),
                    company.get('address'),
                    'China',
                    'China',
                    'CMEF 2025',
                    company.get('product_category'),
                    company.get('product_keywords', []),
                    company.get('category_confidence'),
                    company.get('website_validated', False),
                    company.get('website_status_code'),
                    'CMEF'
                )
                inserted += 1

                if i % 500 == 0:
                    logger.info(f"  Progress: {i}/{len(companies)} ({inserted} inserted, {skipped} skipped)")

        logger.info(f"✅ Imported {inserted} CMEF companies ({skipped} skipped - no name)")

        # Step 3: Import MEDICA Data
        logger.info("\n" + "=" * 70)
        logger.info("STEP 3: IMPORTING MEDICA DATA")
        logger.info("=" * 70)

        medica_file = '/Users/gabrielreginatto/Desktop/Code/Medical/Medica/china_exhibitors_enriched.json'
        logger.info(f"📖 Loading: {medica_file}")

        with open(medica_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        companies = data.get('exhibitors', [])
        logger.info(f"✅ Loaded {len(companies)} MEDICA companies")

        insert_sql = """
            INSERT INTO medical_exhibitors (
                name, location, company_description,
                email, phone, website, address, raw_text,
                country, region, event,
                product_category, product_keywords, category_confidence,
                data_source, scraped_at
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, NOW()
            )
            ON CONFLICT (name, event) DO NOTHING
        """

        logger.info("💾 Inserting MEDICA companies...")
        inserted = 0
        skipped = 0
        async with conn.transaction():
            for i, company in enumerate(companies, 1):
                # Skip companies without names
                if not company.get('name'):
                    skipped += 1
                    continue

                await conn.execute(insert_sql,
                    company.get('name'),
                    company.get('location'),
                    company.get('company_description'),
                    company.get('email'),
                    company.get('phone'),
                    company.get('website'),
                    company.get('address'),
                    company.get('raw_text'),
                    company.get('country', 'Unknown'),
                    company.get('region', 'Unknown'),
                    'MEDICA 2025',
                    company.get('product_category'),
                    company.get('product_keywords', []),
                    company.get('category_confidence'),
                    'MEDICA'
                )
                inserted += 1

                if i % 500 == 0:
                    logger.info(f"  Progress: {i}/{len(companies)} ({inserted} inserted, {skipped} skipped)")

        logger.info(f"✅ Imported {inserted} MEDICA companies ({skipped} skipped - no name)")

        # Step 4: Print Summary
        logger.info("\n" + "=" * 70)
        logger.info("DATABASE SUMMARY")
        logger.info("=" * 70)

        rows = await conn.fetch("""
            SELECT
                data_source,
                COUNT(*) as total,
                COUNT(product_category) as classified
            FROM medical_exhibitors
            GROUP BY data_source
            ORDER BY data_source
        """)

        total_all = 0
        logger.info("\n📊 By Data Source:")
        for row in rows:
            total_all += row['total']
            pct = row['classified'] / row['total'] * 100 if row['total'] > 0 else 0
            logger.info(f"  {row['data_source']}: {row['total']} companies ({row['classified']} classified, {pct:.1f}%)")

        logger.info(f"\n📈 TOTAL: {total_all} companies")

        # Top categories
        rows = await conn.fetch("""
            SELECT
                product_category,
                COUNT(*) FILTER (WHERE data_source = 'MEDICA') as medica_count,
                COUNT(*) FILTER (WHERE data_source = 'CMEF') as cmef_count,
                COUNT(*) as total_count
            FROM medical_exhibitors
            WHERE product_category IS NOT NULL
            GROUP BY product_category
            ORDER BY total_count DESC
            LIMIT 10
        """)

        logger.info("\n📂 Top 10 Categories:")
        for row in rows:
            logger.info(f"  {row['product_category']}: {row['total_count']} "
                       f"(MEDICA: {row['medica_count']}, CMEF: {row['cmef_count']})")

        logger.info("\n" + "=" * 70)
        logger.info("✅ SETUP COMPLETED SUCCESSFULLY!")
        logger.info("=" * 70)
        logger.info("\nNext steps:")
        logger.info("  1. Query the database: SELECT * FROM medical_exhibitors LIMIT 10;")
        logger.info("  2. Update Looker to use medical_exhibitors database")
        logger.info("  3. Create dashboards with data_source filter")

    except Exception as e:
        logger.error(f"\n❌ Setup failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise
    finally:
        await conn.close()


async def main():
    """Main entry point"""
    await setup_unified_database()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
