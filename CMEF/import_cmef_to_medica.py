#!/usr/bin/env python3
"""
Import CMEF Companies to Unified MEDICA Database

This script imports CMEF 2025 companies into the medica_exhibitors table
with data_source = 'CMEF' for clear source tracking.
"""

import json
import logging
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import CloudSQLManager, create_db_manager_from_env

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/cmef_import.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class CMEFImporter:
    """Import CMEF companies to unified medica_exhibitors table"""

    def __init__(self, db_manager: CloudSQLManager):
        self.db_manager = db_manager

    async def import_companies(self, input_file: str = None):
        """Import CMEF companies to medica_exhibitors table"""

        input_file = input_file or 'data/enriched_companies.json'

        logger.info("=" * 70)
        logger.info("CMEF → MEDICA DATABASE IMPORT")
        logger.info("=" * 70)

        # Load CMEF data
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        companies = data.get('companies', [])
        logger.info(f"Loaded {len(companies)} CMEF companies")

        # Connect to database
        conn = await self.db_manager.get_connection()

        try:
            # Insert companies
            logger.info("\nInserting CMEF companies into medica_exhibitors...")

            insert_sql = """
            INSERT INTO medica_exhibitors (
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
                    # Map CMEF fields to MEDICA schema
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
                        logger.info(f"Imported {i}/{len(companies)} companies")

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
        logger.info("DATABASE SUMMARY - UNIFIED CATALOG")
        logger.info("=" * 70)

        # Total by source
        rows = await conn.fetch("""
            SELECT
                data_source,
                COUNT(*) as total,
                COUNT(product_category) as classified,
                AVG(category_confidence) as avg_confidence
            FROM medica_exhibitors
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
            SELECT event, COUNT(*) as count
            FROM medica_exhibitors
            GROUP BY event
            ORDER BY count DESC
        """)

        logger.info("\nBy Event:")
        for row in rows:
            logger.info(f"  {row['event']}: {row['count']}")

        # Top categories (CMEF only)
        rows = await conn.fetch("""
            SELECT product_category, COUNT(*) as count
            FROM medica_exhibitors
            WHERE data_source = 'CMEF' AND product_category IS NOT NULL
            GROUP BY product_category
            ORDER BY count DESC
            LIMIT 10
        """)

        logger.info("\nTop 10 CMEF Categories:")
        for row in rows:
            logger.info(f"  {row['product_category']}: {row['count']}")


async def main():
    """Main entry point"""
    import asyncio

    logger.info("Starting CMEF import to unified MEDICA database...")

    # Create database manager
    db_manager = create_db_manager_from_env()

    # Import companies
    importer = CMEFImporter(db_manager)
    await importer.import_companies()

    logger.info("\n✅ CMEF import completed successfully!")
    logger.info("\n🎉 Unified database ready!")
    logger.info("\nNext steps:")
    logger.info("  1. Run: python3 classify_medica_companies.py (to classify existing MEDICA companies)")
    logger.info("  2. Update Looker views with new dimensions")
    logger.info("  3. Create unified dashboards")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
