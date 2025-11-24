#!/usr/bin/env python3
"""
Classify Existing MEDICA Companies

Uses the same Gemini AI classification as CMEF to enrich existing
MEDICA companies with product categories and keywords.
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
        logging.FileHandler('logs/medica_classification.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class MedicaClassifier:
    """Classify existing MEDICA companies"""

    def __init__(self, db_manager: CloudSQLManager):
        self.db_manager = db_manager
        self.gemini_client = GeminiParserClient(DEFAULT_CONFIG)

    async def classify_companies(self):
        """Classify all MEDICA companies without categories"""

        logger.info("=" * 70)
        logger.info("MEDICA COMPANIES CLASSIFICATION")
        logger.info("=" * 70)

        conn = await self.db_manager.get_connection()

        try:
            # Get MEDICA companies without classification
            rows = await conn.fetch("""
                SELECT id, name, company_description
                FROM medica_exhibitors
                WHERE data_source = 'MEDICA'
                  AND (product_category IS NULL OR product_category = '')
                  AND company_description IS NOT NULL
                  AND company_description != ''
                ORDER BY id
            """)

            companies = [dict(row) for row in rows]
            logger.info(f"Found {len(companies)} MEDICA companies to classify")

            if not companies:
                logger.info("No companies need classification!")
                return

            # Classify each company
            logger.info("\nClassifying companies using Gemini AI...")

            for i, company in enumerate(companies, 1):
                try:
                    # Use same classification as CMEF
                    category_data = self.gemini_client.classify_product_category(
                        company['company_description']
                    )

                    # Update database
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

                    if i % 10 == 0:
                        logger.info(f"Classified {i}/{len(companies)} companies")

                except Exception as e:
                    logger.warning(f"Failed to classify company {company['id']}: {e}")
                    continue

            logger.info(f"\n✅ Successfully classified {len(companies)} MEDICA companies")

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
        logger.info("CLASSIFICATION SUMMARY")
        logger.info("=" * 70)

        # Overall stats
        row = await conn.fetchrow("""
            SELECT
                COUNT(*) as total,
                COUNT(product_category) as classified,
                AVG(category_confidence) as avg_confidence
            FROM medica_exhibitors
            WHERE data_source = 'MEDICA'
        """)

        logger.info(f"\nMEDICA Companies:")
        logger.info(f"  Total: {row['total']}")
        logger.info(f"  Classified: {row['classified']}")
        logger.info(f"  Average Confidence: {row['avg_confidence']:.2f if row['avg_confidence'] else 0}")

        # Top categories
        rows = await conn.fetch("""
            SELECT product_category, COUNT(*) as count
            FROM medica_exhibitors
            WHERE data_source = 'MEDICA' AND product_category IS NOT NULL
            GROUP BY product_category
            ORDER BY count DESC
            LIMIT 10
        """)

        logger.info("\nTop 10 MEDICA Categories:")
        for row in rows:
            logger.info(f"  {row['product_category']}: {row['count']}")


async def main():
    """Main entry point"""
    logger.info("Starting MEDICA companies classification...")

    # Create database manager
    db_manager = create_db_manager_from_env()

    # Classify companies
    classifier = MedicaClassifier(db_manager)
    await classifier.classify_companies()

    logger.info("\n✅ MEDICA classification completed successfully!")
    logger.info("\n🎉 All companies now have product categories!")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
