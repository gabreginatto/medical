#!/usr/bin/env python3
"""
Step 3: Classify Product Categories

Classifies companies into product categories and extracts keywords.
NOTE: NCM codes and ANVISA risk classifications will be added in a separate enrichment step.
"""

import json
import logging
from datetime import datetime
from collections import Counter

from config import CMEFConfig, DEFAULT_CONFIG
from utils.gemini_client import GeminiParserClient

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/classification.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ProductClassifier:
    """Classifies company products into categories"""

    def __init__(self, config: CMEFConfig = DEFAULT_CONFIG):
        self.config = config
        self.gemini_client = GeminiParserClient(config)

    def classify_companies(self, input_file: str = None) -> dict:
        """Classify company data into product categories"""
        input_file = input_file or self.config.get_full_path(self.config.STRUCTURED_OUTPUT_FILE)

        logger.info("=" * 70)
        logger.info("STEP 3: PRODUCT CLASSIFICATION")
        logger.info("=" * 70)

        # Load structured data
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        companies = data.get('companies', [])
        logger.info(f"Loaded {len(companies)} companies")

        # Classify product categories using Gemini
        logger.info("\nClassifying product categories using Gemini AI...")
        logger.info("This extracts: category + product keywords from scope descriptions")

        for i, company in enumerate(companies, 1):
            scope = company.get('scope_description', '')

            if scope:
                try:
                    category_data = self.gemini_client.classify_product_category(scope)
                    company['product_category'] = category_data.get('category', 'Other Medical Equipment')
                    company['product_keywords'] = category_data.get('product_keywords', [])
                    company['category_confidence'] = category_data.get('confidence', 0.0)
                except Exception as e:
                    logger.warning(f"Classification failed for company {i}: {e}")
                    company['product_category'] = 'Other Medical Equipment'
                    company['product_keywords'] = []
                    company['category_confidence'] = 0.0
            else:
                company['product_category'] = 'Other Medical Equipment'
                company['product_keywords'] = []
                company['category_confidence'] = 0.0

            # Set NCM and ANVISA to null (will be enriched later)
            company['ncm_code'] = None
            company['anvisa_risk_class'] = None

            if i % 10 == 0:
                logger.info(f"Classified {i}/{len(companies)} companies")

        logger.info("✅ Classification complete!")

        # Generate statistics
        self._print_statistics(companies)

        # Save enriched data
        output_data = {
            'classified_at': datetime.now().isoformat(),
            'total_companies': len(companies),
            'companies': companies,
            'note': 'NCM codes and ANVISA risk classifications are null. Run enrichment step to add them.'
        }

        output_file = self.config.get_full_path(self.config.ENRICHED_OUTPUT_FILE)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        logger.info(f"\n✅ Saved classified data to {output_file}")
        logger.info(f"\nNext step: Run step4_save_database.py")

        return output_data

    def _print_statistics(self, companies: list):
        """Print classification statistics"""
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


def main():
    classifier = ProductClassifier()

    try:
        classifier.classify_companies()
        logger.info("\n✅ Classification completed successfully!")
    except Exception as e:
        logger.error(f"\n❌ Error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise


if __name__ == "__main__":
    main()
