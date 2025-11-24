#!/usr/bin/env python3
"""
Classify Companies in Unified Database

Uses Gemini AI to classify all unclassified companies in the unified database.
This enriches existing MEDICA companies with product categories and keywords.
"""

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncpg
from utils.gemini_client import GeminiParserClient
from config import DEFAULT_CONFIG

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/unified_classification.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class UnifiedClassifier:
    """Classify unclassified companies in unified database"""

    def __init__(self, db_url: str):
        self.db_url = db_url
        self.gemini_client = GeminiParserClient(DEFAULT_CONFIG)

    async def classify_companies(self, data_source: str = None):
        """
        Classify all companies without categories

        Args:
            data_source: Optional filter ('MEDICA' or 'CMEF'). If None, classifies all.
        """

        logger.info("=" * 70)
        logger.info("UNIFIED DATABASE CLASSIFICATION")
        logger.info("=" * 70)
        logger.info(f"Target: {data_source if data_source else 'ALL companies'}")
        logger.info(f"Model: {DEFAULT_CONFIG.GEMINI_MODEL}")
        logger.info("=" * 70)

        conn = await asyncpg.connect(self.db_url)

        try:
            # Build query based on filter
            query = """
                SELECT id, name, company_description, data_source
                FROM medical_exhibitors
                WHERE (product_category IS NULL OR product_category = '')
                  AND company_description IS NOT NULL
                  AND company_description != ''
            """

            params = []
            if data_source:
                query += " AND data_source = $1"
                params.append(data_source)

            query += " ORDER BY id"

            # Get unclassified companies
            rows = await conn.fetch(query, *params)
            companies = [dict(row) for row in rows]

            logger.info(f"\n📊 Found {len(companies)} companies to classify")

            if not companies:
                logger.info("✅ No companies need classification!")
                await self._print_summary(conn)
                return

            # Show breakdown by source
            if not data_source:
                for source in ['MEDICA', 'CMEF']:
                    count = sum(1 for c in companies if c['data_source'] == source)
                    logger.info(f"  {source}: {count} companies")

            # Classify each company
            logger.info(f"\n🤖 Classifying companies using Gemini AI...")

            success_count = 0
            error_count = 0

            for i, company in enumerate(companies, 1):
                try:
                    # Use Gemini to classify
                    category_data = self.gemini_client.classify_product_category(
                        company['company_description']
                    )

                    # Update database
                    await conn.execute("""
                        UPDATE medical_exhibitors
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
                    logger.warning(f"  Failed to classify company {company['id']} ({company['name']}): {e}")
                    continue

            logger.info(f"\n✅ Classification complete!")
            logger.info(f"  Success: {success_count}")
            logger.info(f"  Errors: {error_count}")

            # Print summary
            await self._print_summary(conn)

        except Exception as e:
            logger.error(f"❌ Classification error: {e}")
            raise
        finally:
            await conn.close()

    async def _print_summary(self, conn):
        """Print classification statistics"""
        logger.info("\n" + "=" * 70)
        logger.info("UNIFIED DATABASE SUMMARY")
        logger.info("=" * 70)

        # Overall stats by source
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
            classified_pct = (row['classified'] / row['total'] * 100) if row['total'] > 0 else 0
            logger.info(f"  {row['data_source']}: {row['total']} companies")
            logger.info(f"    Classified: {row['classified']} ({classified_pct:.1f}%)")
            logger.info(f"    Avg Confidence: {row['avg_confidence']:.2f if row['avg_confidence'] else 0}")

        # Top categories (overall)
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
            LIMIT 15
        """)

        logger.info("\nTop 15 Product Categories (Unified):")
        for row in rows:
            logger.info(f"  {row['product_category']}: {row['total_count']} "
                       f"(MEDICA: {row['medica_count']}, CMEF: {row['cmef_count']})")

        # Total stats
        total = await conn.fetchval("SELECT COUNT(*) FROM medical_exhibitors")
        classified = await conn.fetchval(
            "SELECT COUNT(*) FROM medical_exhibitors WHERE product_category IS NOT NULL"
        )
        unclassified = total - classified

        logger.info("\n" + "=" * 70)
        logger.info(f"TOTAL COMPANIES: {total}")
        logger.info(f"CLASSIFIED: {classified} ({classified/total*100:.1f}%)")
        logger.info(f"UNCLASSIFIED: {unclassified} ({unclassified/total*100:.1f}%)")
        logger.info("=" * 70)


async def main():
    """Main entry point"""
    import os
    import sys

    logger.info("Starting unified database classification...")

    # Database connection string
    db_url = os.getenv('UNIFIED_DB_URL') or input(
        "Enter unified database URL:\n"
        "Format: postgresql://user:password@host:5432/medical_unified\n> "
    )

    # Ask which data source to classify
    print("\n" + "=" * 70)
    print("CLASSIFICATION OPTIONS")
    print("=" * 70)
    print("1. Classify MEDICA companies only")
    print("2. Classify CMEF companies only")
    print("3. Classify ALL companies")
    print("=" * 70)

    choice = input("\nSelect option (1-3): ").strip()

    data_source = None
    if choice == '1':
        data_source = 'MEDICA'
    elif choice == '2':
        data_source = 'CMEF'
    elif choice == '3':
        data_source = None
    else:
        logger.error("❌ Invalid choice")
        return

    # Confirm before proceeding
    print("\n" + "=" * 70)
    print("CLASSIFICATION PLAN")
    print("=" * 70)
    print(f"💾 Database: {db_url.split('@')[1] if '@' in db_url else db_url}")
    print(f"🎯 Target: {data_source if data_source else 'ALL companies'}")
    print(f"🤖 Model: {DEFAULT_CONFIG.GEMINI_MODEL}")
    print("\nThis operation will:")
    print("  1. Find all unclassified companies")
    print("  2. Use Gemini AI to classify products")
    print("  3. Update product_category and product_keywords")
    print("=" * 70)

    confirm = input("\nProceed with classification? (yes/no): ").strip().lower()
    if confirm != 'yes':
        logger.info("❌ Classification cancelled by user")
        return

    # Run classification
    classifier = UnifiedClassifier(db_url)
    await classifier.classify_companies(data_source)

    logger.info("\n✅ Classification completed successfully!")
    logger.info("\n🎉 Unified database fully enriched!")
    logger.info("\nNext steps:")
    logger.info("  1. Update Looker connection to point to new database")
    logger.info("  2. Create unified dashboards with data_source filter")
    logger.info("  3. Test product keyword search functionality")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
