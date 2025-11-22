#!/usr/bin/env python3
"""
Step 2: Parse and Structure

Parses OCR text and extracts structured company data using Gemini AI.
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path

from config import CMEFConfig, DEFAULT_CONFIG
from utils.gemini_client import AsyncGeminiProcessor
from utils.validator import DataValidator

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/parsing.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class DataParser:
    """Parses OCR output and structures company data"""

    def __init__(self, config: CMEFConfig = DEFAULT_CONFIG):
        self.config = config
        self.gemini_processor = AsyncGeminiProcessor(config)
        self.validator = DataValidator(config)

    async def parse_ocr_output(self, input_file: str = None) -> dict:
        """Parse OCR output and extract structured data"""
        input_file = input_file or self.config.get_full_path(self.config.OCR_OUTPUT_FILE)

        logger.info("=" * 70)
        logger.info("STEP 2: PARSE AND STRUCTURE")
        logger.info("=" * 70)

        # Load OCR results
        logger.info(f"Loading OCR results from {input_file}...")
        with open(input_file, 'r', encoding='utf-8') as f:
            ocr_data = json.load(f)

        pages = ocr_data.get('pages', [])
        logger.info(f"Loaded {len(pages)} pages of OCR text")

        # Combine page texts (group pages into company entries)
        # Simple heuristic: each company might span 1-2 pages
        ocr_texts = [page['text'] for page in pages if page.get('text')]

        logger.info(f"\nParsing {len(ocr_texts)} text blocks...")

        # Parse using Gemini
        companies = await self.gemini_processor.process_all_batches(ocr_texts)

        logger.info(f"\nExtracted {len(companies)} company records")

        # Validate and clean data
        logger.info("\nValidating company data...")
        validated_companies = []
        all_issues = []

        for company in companies:
            validated, issues = self.validator.validate_company(company)
            validated_companies.append(validated)
            if issues:
                all_issues.append({
                    'company': company.get('company_name_en', 'Unknown'),
                    'issues': issues
                })

        logger.info(f"Validation complete: {len(all_issues)} companies with issues")

        # Validate websites (async)
        if self.config.VALIDATE_WEBSITES:
            logger.info("\nValidating website accessibility...")
            validated_companies = await self.validator.validate_websites_batch(validated_companies)

        # Generate validation report
        validation_report = self.validator.generate_validation_report(validated_companies)
        self.validator.print_validation_report(validation_report)

        # Save results
        output_data = {
            'parsed_at': datetime.now().isoformat(),
            'total_companies': len(validated_companies),
            'validation_report': validation_report,
            'issues': all_issues,
            'companies': validated_companies
        }

        output_file = self.config.get_full_path(self.config.STRUCTURED_OUTPUT_FILE)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        logger.info(f"\n✅ Saved {len(validated_companies)} companies to {output_file}")
        logger.info(f"\nNext step: Run step3_classify_enrich.py")

        return output_data


async def main():
    parser = DataParser()

    try:
        await parser.parse_ocr_output()
        logger.info("\n✅ Parsing completed successfully!")
    except Exception as e:
        logger.error(f"\n❌ Error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise


if __name__ == "__main__":
    asyncio.run(main())
