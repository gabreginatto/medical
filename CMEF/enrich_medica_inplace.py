#!/usr/bin/env python3
"""
Enrich Existing MEDICA Database (In-Place)

Uses the same Gemini AI classification as CMEF Step 3 to enrich existing
MEDICA companies with product categories and keywords.

IMPORTANT: This modifies the existing 'medical' database by adding new columns.
It does NOT delete or modify existing data.
"""

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import CloudSQLManager, create_db_manager_from_env
from utils.gemini_client import GeminiParserClient
from config import DEFAULT_CONFIG

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/medica_enrichment.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class MedicaEnricher:
    """Enrich existing MEDICA companies with AI classification"""

    def __init__(self, db_manager: CloudSQLManager):
        self.db_manager = db_manager
        self.gemini_client = GeminiParserClient(DEFAULT_CONFIG)

    async def add_classification_columns(self):
        """Add classification columns to medica_exhibitors table if they don't exist"""

        logger.info("Checking if classification columns exist...")

        conn = await self.db_manager.get_connection()

        try:
            # Check if columns already exist
            existing_columns = await conn.fetch("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'medica_exhibitors'
                AND column_name IN ('product_category', 'product_keywords', 'category_confidence')
            """)

            existing_column_names = [row['column_name'] for row in existing_columns]

            if len(existing_column_names) == 3:
                logger.info("✅ All classification columns already exist")
                return True

            # Add missing columns
            logger.info("Adding classification columns to medica_exhibitors table...")

            alter_statements = []

            if 'product_category' not in existing_column_names:
                alter_statements.append("ADD COLUMN IF NOT EXISTS product_category VARCHAR(200)")

            if 'product_keywords' not in existing_column_names:
                alter_statements.append("ADD COLUMN IF NOT EXISTS product_keywords TEXT[]")

            if 'category_confidence' not in existing_column_names:
                alter_statements.append("ADD COLUMN IF NOT EXISTS category_confidence FLOAT")

            if alter_statements:
                alter_sql = f"ALTER TABLE medica_exhibitors {', '.join(alter_statements)}"
                await conn.execute(alter_sql)
                logger.info("✅ Classification columns added successfully")

            # Create GIN index for keyword search if it doesn't exist
            logger.info("Creating GIN index for product_keywords...")
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_medica_keywords
                ON medica_exhibitors USING GIN(product_keywords)
            """)

            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_medica_category
                ON medica_exhibitors(product_category)
            """)

            logger.info("✅ Indexes created successfully")

            return True

        except Exception as e:
            logger.error(f"❌ Error adding columns: {e}")
            raise
        finally:
            await conn.close()

    async def enrich_companies(self):
        """Classify all MEDICA companies without categories"""

        logger.info("=" * 70)
        logger.info("MEDICA DATABASE ENRICHMENT")
        logger.info("=" * 70)
        logger.info(f"Model: {DEFAULT_CONFIG.GEMINI_MODEL}")
        logger.info("=" * 70)

        # First ensure columns exist
        await self.add_classification_columns()

        conn = await self.db_manager.get_connection()

        try:
            # Get MEDICA companies that need classification
            # We classify companies that have descriptions but no category yet
            rows = await conn.fetch("""
                SELECT id, name, company_description
                FROM medica_exhibitors
                WHERE (product_category IS NULL OR product_category = '')
                  AND company_description IS NOT NULL
                  AND company_description != ''
                ORDER BY id
            """)

            companies = [dict(row) for row in rows]
            logger.info(f"\n📊 Found {len(companies)} MEDICA companies to classify")

            if not companies:
                logger.info("✅ No companies need classification!")
                await self._print_summary(conn)
                return

            # Show sample
            logger.info(f"\n📋 Sample company: {companies[0]['name']}")
            logger.info(f"   Description: {companies[0]['company_description'][:100]}...")

            # Classify each company using the SAME logic as CMEF Step 3
            logger.info(f"\n🤖 Classifying companies using Gemini AI...")
            logger.info(f"   This will extract: category + product keywords from descriptions")

            success_count = 0
            error_count = 0

            for i, company in enumerate(companies, 1):
                try:
                    # Use EXACT same method as CMEF Step 3
                    description = company['company_description']

                    category_data = self.gemini_client.classify_product_category(description)

                    # Update database with classification
                    await conn.execute("""
                        UPDATE medica_exhibitors
                        SET
                            product_category = $2,
                            product_keywords = $3,
                            category_confidence = $4,
                            updated_at = NOW()
                        WHERE id = $1
                    """,
                        company['id'],
                        category_data.get('category', 'Other Medical Equipment'),
                        category_data.get('product_keywords', []),
                        category_data.get('confidence', 0.0)
                    )

                    success_count += 1

                    if i % 10 == 0:
                        logger.info(f"  Progress: {i}/{len(companies)} ({success_count} success, {error_count} errors)")

                except Exception as e:
                    error_count += 1
                    logger.warning(f"  Classification failed for company {company['id']} ({company['name']}): {e}")
                    # Set default values for failed classification
                    await conn.execute("""
                        UPDATE medica_exhibitors
                        SET
                            product_category = 'Other Medical Equipment',
                            product_keywords = ARRAY[]::TEXT[],
                            category_confidence = 0.0,
                            updated_at = NOW()
                        WHERE id = $1
                    """, company['id'])
                    continue

            logger.info(f"\n✅ Classification complete!")
            logger.info(f"  Success: {success_count}")
            logger.info(f"  Errors: {error_count}")

            # Print summary
            await self._print_summary(conn)

        except Exception as e:
            logger.error(f"❌ Enrichment error: {e}")
            raise
        finally:
            await conn.close()

    async def _print_summary(self, conn):
        """Print classification statistics"""
        logger.info("\n" + "=" * 70)
        logger.info("MEDICA DATABASE SUMMARY")
        logger.info("=" * 70)

        # Overall stats
        row = await conn.fetchrow("""
            SELECT
                COUNT(*) as total,
                COUNT(product_category) as classified,
                COUNT(*) - COUNT(product_category) as unclassified,
                AVG(category_confidence) as avg_confidence
            FROM medica_exhibitors
        """)

        logger.info(f"\n📊 Overall Statistics:")
        logger.info(f"  Total companies: {row['total']}")
        logger.info(f"  Classified: {row['classified']} ({row['classified']/row['total']*100:.1f}%)")
        logger.info(f"  Unclassified: {row['unclassified']} ({row['unclassified']/row['total']*100:.1f}%)")
        logger.info(f"  Avg Confidence: {row['avg_confidence']:.2f if row['avg_confidence'] else 0}")

        # Top categories
        rows = await conn.fetch("""
            SELECT product_category, COUNT(*) as count
            FROM medica_exhibitors
            WHERE product_category IS NOT NULL
            GROUP BY product_category
            ORDER BY count DESC
            LIMIT 15
        """)

        logger.info("\n📂 Top 15 Product Categories:")
        for row in rows:
            logger.info(f"  {row['product_category']}: {row['count']}")

        # Sample keywords
        rows = await conn.fetch("""
            SELECT name, product_keywords
            FROM medica_exhibitors
            WHERE product_keywords IS NOT NULL
              AND array_length(product_keywords, 1) > 0
            LIMIT 5
        """)

        logger.info("\n🔑 Sample Keywords:")
        for row in rows:
            keywords = ', '.join(row['product_keywords'][:5])
            logger.info(f"  {row['name']}: [{keywords}]")


async def main():
    """Main entry point"""

    logger.info("Starting MEDICA database enrichment...")
    logger.info("\n⚠️  IMPORTANT: This will modify the existing 'medical' database")
    logger.info("   It will add new columns and populate them with AI classifications")
    logger.info("   Existing data will NOT be deleted or modified\n")

    # Confirm before proceeding
    confirm = input("Do you want to proceed? (yes/no): ").strip().lower()
    if confirm != 'yes':
        logger.info("❌ Enrichment cancelled by user")
        return

    # Create database manager from environment variables
    # This will use the existing MEDICA database connection
    db_manager = create_db_manager_from_env()

    # Enrich companies
    enricher = MedicaEnricher(db_manager)
    await enricher.enrich_companies()

    logger.info("\n✅ MEDICA enrichment completed successfully!")
    logger.info("\n🎉 Database now has product categories and keywords!")
    logger.info("\nExample queries:")
    logger.info("  -- Search by keyword:")
    logger.info("  SELECT name, product_category FROM medica_exhibitors WHERE 'ultrasound' = ANY(product_keywords);")
    logger.info("\n  -- Category breakdown:")
    logger.info("  SELECT product_category, COUNT(*) FROM medica_exhibitors GROUP BY product_category ORDER BY count DESC;")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
