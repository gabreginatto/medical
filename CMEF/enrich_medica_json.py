#!/usr/bin/env python3
"""
Enrich MEDICA JSON with AI Classification

Uses EXACT same logic as CMEF Step 3 to classify MEDICA companies.
Works with JSON file instead of database for safety.

Input:  /Users/gabrielreginatto/Desktop/Code/Medical/Medica/china_exhibitors_with_gcs_urls.json
Output: /Users/gabrielreginatto/Desktop/Code/Medical/Medica/china_exhibitors_enriched.json
"""

import json
import logging
from datetime import datetime
from collections import Counter
from pathlib import Path

from config import DEFAULT_CONFIG
from utils.gemini_client import GeminiParserClient

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/medica_json_enrichment.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class MedicaJSONEnricher:
    """Enrich MEDICA JSON with product classification"""

    def __init__(self):
        self.gemini_client = GeminiParserClient(DEFAULT_CONFIG)

    def enrich_companies(
        self,
        input_file: str = None,
        output_file: str = None
    ) -> dict:
        """
        Classify MEDICA companies from JSON file

        Args:
            input_file: Path to china_exhibitors_with_gcs_urls.json
            output_file: Path for enriched output (default: china_exhibitors_enriched.json)
        """

        # Default paths
        input_file = input_file or '/Users/gabrielreginatto/Desktop/Code/Medical/Medica/china_exhibitors_with_gcs_urls.json'
        output_file = output_file or '/Users/gabrielreginatto/Desktop/Code/Medical/Medica/china_exhibitors_enriched.json'

        logger.info("=" * 70)
        logger.info("MEDICA JSON ENRICHMENT (SAME AS CMEF STEP 3)")
        logger.info("=" * 70)
        logger.info(f"Model: {DEFAULT_CONFIG.GEMINI_MODEL}")
        logger.info(f"Input:  {input_file}")
        logger.info(f"Output: {output_file}")
        logger.info("=" * 70)

        # Load MEDICA data
        logger.info("\n📖 Loading MEDICA data...")
        with open(input_file, 'r', encoding='utf-8') as f:
            companies = json.load(f)

        if isinstance(companies, dict):
            companies = companies.get('exhibitors', [])

        logger.info(f"✅ Loaded {len(companies)} MEDICA companies")

        # Show sample
        if companies:
            sample = companies[0]
            logger.info(f"\n📋 Sample company:")
            logger.info(f"  Name: {sample.get('name')}")
            logger.info(f"  Location: {sample.get('location')}")
            logger.info(f"  Description: {sample.get('company_description', '')[:100]}...")

        # Classify using EXACT same logic as CMEF Step 3
        logger.info("\n🤖 Classifying product categories using Gemini AI...")
        logger.info("   (Same classification logic as CMEF Step 3)")

        success_count = 0
        error_count = 0

        for i, company in enumerate(companies, 1):
            # Use company_description field (same as CMEF's scope_description)
            description = company.get('company_description', '')

            if description and description.strip():
                try:
                    # EXACT SAME METHOD as CMEF Step 3
                    category_data = self.gemini_client.classify_product_category(description)

                    company['product_category'] = category_data.get('category', 'Other Medical Equipment')
                    company['product_keywords'] = category_data.get('product_keywords', [])
                    company['category_confidence'] = category_data.get('confidence', 0.0)

                    success_count += 1

                except Exception as e:
                    logger.warning(f"  Classification failed for company {i} ({company.get('name')}): {e}")
                    company['product_category'] = 'Other Medical Equipment'
                    company['product_keywords'] = []
                    company['category_confidence'] = 0.0
                    error_count += 1
            else:
                # No description - set defaults
                company['product_category'] = 'Other Medical Equipment'
                company['product_keywords'] = []
                company['category_confidence'] = 0.0

            if i % 10 == 0:
                logger.info(f"  Progress: {i}/{len(companies)} ({success_count} success, {error_count} errors)")

        logger.info(f"\n✅ Classification complete!")
        logger.info(f"  Success: {success_count}")
        logger.info(f"  Errors: {error_count}")

        # Generate statistics (same as CMEF)
        self._print_statistics(companies)

        # Save enriched data
        output_data = {
            'enriched_at': datetime.now().isoformat(),
            'model': DEFAULT_CONFIG.GEMINI_MODEL,
            'total_companies': len(companies),
            'classified_companies': success_count,
            'source': 'MEDICA',
            'exhibitors': companies
        }

        logger.info(f"\n💾 Saving enriched data to {output_file}...")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        logger.info(f"✅ Saved enriched data successfully!")

        # Print file sizes
        input_size = Path(input_file).stat().st_size / (1024 * 1024)
        output_size = Path(output_file).stat().st_size / (1024 * 1024)
        logger.info(f"\n📁 File sizes:")
        logger.info(f"  Input:  {input_size:.2f} MB")
        logger.info(f"  Output: {output_size:.2f} MB")

        return output_data

    def _print_statistics(self, companies: list):
        """Print classification statistics (same format as CMEF)"""
        logger.info("\n" + "=" * 70)
        logger.info("CLASSIFICATION STATISTICS")
        logger.info("=" * 70)

        logger.info(f"\nTotal companies: {len(companies)}")

        # Category distribution
        categories = [c.get('product_category', 'Unknown') for c in companies]
        category_counts = Counter(categories)

        logger.info("\nProduct Category Distribution:")
        for category, count in category_counts.most_common(15):
            percentage = (count / len(companies)) * 100
            logger.info(f"  {category}: {count} ({percentage:.1f}%)")

        # Average confidence
        confidences = [c.get('category_confidence', 0.0) for c in companies]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        logger.info(f"\nAverage classification confidence: {avg_confidence:.2f}")

        # Keywords stats
        total_keywords = sum(len(c.get('product_keywords', [])) for c in companies)
        avg_keywords = total_keywords / len(companies) if companies else 0
        logger.info(f"Total keywords extracted: {total_keywords}")
        logger.info(f"Average keywords per company: {avg_keywords:.1f}")

        # Companies with descriptions
        with_desc = sum(1 for c in companies if c.get('company_description'))
        logger.info(f"\nCompanies with descriptions: {with_desc} ({with_desc/len(companies)*100:.1f}%)")


def main():
    """Main entry point"""

    logger.info("Starting MEDICA JSON enrichment...")
    logger.info("This uses EXACT same classification logic as CMEF Step 3\n")

    enricher = MedicaJSONEnricher()

    try:
        enricher.enrich_companies()

        logger.info("\n" + "=" * 70)
        logger.info("✅ MEDICA ENRICHMENT COMPLETED SUCCESSFULLY!")
        logger.info("=" * 70)
        logger.info("\nNext steps:")
        logger.info("  1. Review: /Users/gabrielreginatto/Desktop/Code/Medical/Medica/china_exhibitors_enriched.json")
        logger.info("  2. Import to database (optional)")
        logger.info("  3. Compare with CMEF categories")
        logger.info("")

    except Exception as e:
        logger.error(f"\n❌ Error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise


if __name__ == "__main__":
    main()
