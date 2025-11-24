#!/usr/bin/env python3
"""
Import CMEF Companies to Unified Database

Imports CMEF 2025 companies into the new medical_unified database
with data_source = 'CMEF' for clear source tracking.
"""

import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncpg

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/cmef_unified_import.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class CMEFUnifiedImporter:
    """Import CMEF companies to unified medical_exhibitors table"""

    def __init__(self, db_url: str):
        self.db_url = db_url

    async def import_companies(self, input_file: str = None):
        """Import CMEF companies to medical_exhibitors table"""

        input_file = input_file or 'data/enriched_companies.json'

        logger.info("=" * 70)
        logger.info("CMEF → UNIFIED DATABASE IMPORT")
        logger.info("=" * 70)

        # Load CMEF data
        logger.info(f"\n📖 Loading CMEF data from {input_file}...")
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        companies = data.get('companies', [])
        logger.info(f"✅ Loaded {len(companies)} CMEF companies")

        if not companies:
            logger.error("❌ No companies found in input file!")
            return

        # Show sample company
        logger.info(f"\n📋 Sample company:")
        sample = companies[0]
        logger.info(f"  Name: {sample.get('company_name_en')}")
        logger.info(f"  Chinese: {sample.get('company_name_zh')}")
        logger.info(f"  Booth: {sample.get('booth_number')}")
        logger.info(f"  Category: {sample.get('product_category')}")
        logger.info(f"  Keywords: {sample.get('product_keywords', [])[:3]}")

        # Connect to database
        logger.info("\n📡 Connecting to unified database...")
        conn = await asyncpg.connect(self.db_url)

        try:
            # Insert companies
            logger.info(f"\n💾 Inserting {len(companies)} CMEF companies...")

            insert_sql = """
            INSERT INTO medical_exhibitors (
                name,
                company_name_zh,
                location,
                booth_number,
                company_description,
                email,
                phone,
                website,
                address,
                country,
                region,
                event,
                product_category,
                product_keywords,
                category_confidence,
                website_validated,
                website_status_code,
                data_source,
                scraped_at
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, NOW()
            )
            ON CONFLICT (name, event) DO UPDATE SET
                company_name_zh = EXCLUDED.company_name_zh,
                booth_number = EXCLUDED.booth_number,
                product_category = EXCLUDED.product_category,
                product_keywords = EXCLUDED.product_keywords,
                category_confidence = EXCLUDED.category_confidence,
                website_validated = EXCLUDED.website_validated,
                website_status_code = EXCLUDED.website_status_code,
                updated_at = NOW()
            """

            async with conn.transaction():
                for i, company in enumerate(companies, 1):
                    # Map CMEF fields to unified schema
                    await conn.execute(insert_sql,
                        company.get('company_name_en'),           # name
                        company.get('company_name_zh'),           # company_name_zh
                        company.get('booth_number'),              # location (booth as location)
                        company.get('booth_number'),              # booth_number
                        company.get('scope_description'),         # company_description
                        company.get('email'),                     # email
                        company.get('phone'),                     # phone
                        company.get('website'),                   # website
                        company.get('address'),                   # address
                        'China',                                  # country
                        'China',                                  # region
                        'CMEF 2025',                             # event
                        company.get('product_category'),          # product_category
                        company.get('product_keywords', []),      # product_keywords
                        company.get('category_confidence'),       # category_confidence
                        company.get('website_validated', False),  # website_validated
                        company.get('website_status_code'),       # website_status_code
                        'CMEF'                                    # data_source
                    )

                    if i % 100 == 0:
                        logger.info(f"  Imported {i}/{len(companies)} companies")

            logger.info(f"\n✅ Successfully imported {len(companies)} CMEF companies")

            # Print summary
            await self._print_summary(conn)

        except Exception as e:
            logger.error(f"❌ Import error: {e}")
            raise
        finally:
            await conn.close()

    async def _print_summary(self, conn):
        """Print import statistics"""
        logger.info("\n" + "=" * 70)
        logger.info("UNIFIED DATABASE SUMMARY")
        logger.info("=" * 70)

        # Total by source
        rows = await conn.fetch("""
            SELECT
                data_source,
                COUNT(*) as total,
                COUNT(product_category) as classified,
                AVG(category_confidence) as avg_confidence
            FROM medical_exhibitors
            GROUP BY data_source
            ORDER BY data_source
        """)

        logger.info("\nBy Data Source:")
        for row in rows:
            logger.info(f"  {row['data_source']}: {row['total']} companies "
                       f"({row['classified']} classified, "
                       f"avg confidence: {row['avg_confidence']:.2f if row['avg_confidence'] else 0})")

        # Total by event
        rows = await conn.fetch("""
            SELECT event, data_source, COUNT(*) as count
            FROM medical_exhibitors
            GROUP BY event, data_source
            ORDER BY data_source, event
        """)

        logger.info("\nBy Event:")
        for row in rows:
            logger.info(f"  {row['event']} ({row['data_source']}): {row['count']}")

        # Top categories (CMEF only)
        rows = await conn.fetch("""
            SELECT product_category, COUNT(*) as count
            FROM medical_exhibitors
            WHERE data_source = 'CMEF' AND product_category IS NOT NULL
            GROUP BY product_category
            ORDER BY count DESC
            LIMIT 10
        """)

        logger.info("\nTop 10 CMEF Categories:")
        for row in rows:
            logger.info(f"  {row['product_category']}: {row['count']}")

        # Overall stats
        total = await conn.fetchval("SELECT COUNT(*) FROM medical_exhibitors")
        classified = await conn.fetchval(
            "SELECT COUNT(*) FROM medical_exhibitors WHERE product_category IS NOT NULL"
        )

        logger.info("\n" + "=" * 70)
        logger.info(f"TOTAL: {total} companies")
        logger.info(f"CLASSIFIED: {classified} companies ({classified/total*100:.1f}%)")
        logger.info("=" * 70)


async def main():
    """Main entry point"""
    import os

    logger.info("Starting CMEF import to unified database...")

    # Database connection string
    db_url = os.getenv('UNIFIED_DB_URL') or input(
        "Enter unified database URL:\n"
        "Format: postgresql://user:password@host:5432/medical_unified\n> "
    )

    # Confirm before proceeding
    print("\n" + "=" * 70)
    print("IMPORT PLAN")
    print("=" * 70)
    print(f"📊 Source: data/enriched_companies.json")
    print(f"💾 Target: {db_url.split('@')[1] if '@' in db_url else db_url}")
    print("\nThis operation will:")
    print("  1. Import 4,497 CMEF companies")
    print("  2. Set data_source = 'CMEF' for all records")
    print("  3. Include product categories and keywords")
    print("=" * 70)

    confirm = input("\nProceed with import? (yes/no): ").strip().lower()
    if confirm != 'yes':
        logger.info("❌ Import cancelled by user")
        return

    # Import companies
    importer = CMEFUnifiedImporter(db_url)
    await importer.import_companies()

    logger.info("\n✅ CMEF import completed successfully!")
    logger.info("\n🎉 Unified database now contains both MEDICA and CMEF!")
    logger.info("\nNext steps:")
    logger.info("  1. Run: python3 classify_unified_companies.py (classify MEDICA companies)")
    logger.info("  2. Update Looker connection to point to new database")
    logger.info("  3. Create unified dashboards with data_source filter")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
