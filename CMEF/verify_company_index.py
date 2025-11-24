#!/usr/bin/env python3
"""
Verify Company Index Extraction

OCRs pages 77-129 (company index) and compares with extracted companies
to identify any missing entries.
"""

import asyncio
import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Set

from config import CMEFConfig, DEFAULT_CONFIG
from utils.deepseek_client import DeepSeekOCRClient
from utils.gemini_client import GeminiParserClient

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/index_verification.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class CompanyIndexVerifier:
    """Verifies company extraction by comparing with index pages"""

    def __init__(self, config: CMEFConfig = DEFAULT_CONFIG):
        self.config = config
        self.ocr_client = DeepSeekOCRClient(config)
        self.gemini_client = GeminiParserClient(config)

    async def extract_index_pages(self, start_page: int = 77, end_page: int = 129) -> List[str]:
        """
        OCR the index pages

        Args:
            start_page: First page of index (default: 77)
            end_page: Last page of index (default: 129)

        Returns:
            List of OCR text from each index page
        """
        logger.info("=" * 70)
        logger.info("EXTRACTING COMPANY INDEX")
        logger.info("=" * 70)
        logger.info(f"OCR processing pages {start_page}-{end_page} (company index)")

        # Import PDF processing utilities
        from pdf2image import convert_from_path
        from pathlib import Path

        index_texts = []
        pdf_path = self.config.PDF_PATH

        logger.info(f"Starting OCR extraction from {pdf_path}")

        # Convert PDF pages to images
        logger.info(f"Converting pages {start_page}-{end_page} to images...")
        temp_images_dir = Path(self.config.get_full_path('data/index_images'))
        temp_images_dir.mkdir(exist_ok=True)

        try:
            images = convert_from_path(
                pdf_path,
                dpi=self.config.IMAGE_DPI,
                first_page=start_page,
                last_page=end_page,
                output_folder=str(temp_images_dir),
                fmt='png'
            )

            logger.info(f"✅ Converted {len(images)} pages to images")

            # Save images and process with OCR
            image_paths = []
            for i, image in enumerate(images, start=start_page):
                image_path = temp_images_dir / f"page_{i:04d}.png"
                image.save(image_path, 'PNG')
                image_paths.append(str(image_path))

            logger.info(f"Processing {len(image_paths)} images with DeepSeek OCR...")

            # Process in batches
            batch_size = 15
            for i in range(0, len(image_paths), batch_size):
                batch = image_paths[i:i + batch_size]
                batch_num = i // batch_size + 1
                total_batches = (len(image_paths) + batch_size - 1) // batch_size

                logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} images)")

                batch_results = self.ocr_client.extract_text_from_batch(batch)

                for result in batch_results:
                    if result.get('text'):
                        index_texts.append(result['text'])

                logger.info(f"✅ Extracted {len(batch_results)} pages from batch {batch_num}")

        except Exception as e:
            logger.error(f"Error processing index pages: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise

        logger.info(f"Total index pages extracted: {len(index_texts)}")
        return index_texts

    def parse_index_companies(self, index_texts: List[str]) -> List[Dict]:
        """
        Parse company names from index pages using Gemini

        Args:
            index_texts: OCR text from index pages

        Returns:
            List of company entries from index
        """
        logger.info("\nParsing company names from index...")

        # Combine all index texts
        full_index_text = "\n\n".join(index_texts)

        # Use Gemini to extract structured company list
        prompt = f"""Extract all company names from this company index.

**Index Text:**
{full_index_text[:15000]}

This is an alphabetical index of companies exhibiting at CMEF 2025. Each entry typically contains:
- Company name (English)
- Company name (Chinese, optional)
- Booth number

**Extract ALL company entries and return as JSON array:**
[
  {{
    "company_name_en": "English company name",
    "company_name_zh": "Chinese name (if present)",
    "booth_number": "Booth number (if present)",
    "index_entry": "Original text from index"
  }},
  ...
]

**Instructions:**
- Extract EVERY company mentioned in the index
- Preserve exact company names as written
- Include both English and Chinese names if available
- Extract booth number if present
- Return ONLY the JSON array, no other text
"""

        try:
            response = self.gemini_client.model.generate_content(prompt)
            response_text = response.text.strip()

            # Clean markdown
            if response_text.startswith('```'):
                lines = response_text.split('\n')
                response_text = '\n'.join(
                    line for line in lines
                    if not line.strip().startswith('```')
                )

            companies = json.loads(response_text)
            logger.info(f"✅ Parsed {len(companies)} companies from index")
            return companies

        except Exception as e:
            logger.error(f"Gemini parsing error: {e}")
            # Fallback to regex extraction
            return self._regex_parse_index(full_index_text)

    def _regex_parse_index(self, index_text: str) -> List[Dict]:
        """Fallback regex-based index parsing"""
        logger.warning("Using fallback regex parsing for index")

        companies = []

        # Simple pattern: line with company name
        # Index typically has format: "Company Name ... Booth#"
        lines = index_text.split('\n')

        for line in lines:
            line = line.strip()
            if not line or len(line) < 10:
                continue

            # Look for booth numbers
            booth_match = re.search(r'\b(\d+\.\d+[A-Z]\d+)\b', line)
            booth = booth_match.group(1) if booth_match else None

            # Extract company name (text before booth or full line)
            if booth:
                company_name = line[:booth_match.start()].strip()
            else:
                company_name = line

            # Clean up company name
            company_name = re.sub(r'\s+', ' ', company_name)
            company_name = re.sub(r'\.{2,}', '', company_name)

            if len(company_name) > 5:  # Valid company name
                companies.append({
                    'company_name_en': company_name,
                    'company_name_zh': None,
                    'booth_number': booth,
                    'index_entry': line
                })

        logger.info(f"Regex extracted {len(companies)} company entries")
        return companies

    def compare_with_extracted(
        self,
        index_companies: List[Dict],
        extracted_companies: List[Dict]
    ) -> Dict:
        """
        Compare index companies with extracted companies

        Args:
            index_companies: Companies from index pages
            extracted_companies: Companies from OCR extraction

        Returns:
            Comparison report with missing/extra companies
        """
        logger.info("\n" + "=" * 70)
        logger.info("COMPARING INDEX WITH EXTRACTED COMPANIES")
        logger.info("=" * 70)

        # Create normalized sets for comparison
        index_names = set()
        index_booths = set()

        for company in index_companies:
            name = company.get('company_name_en', '').strip().lower()
            booth = company.get('booth_number', '').strip()

            if name:
                index_names.add(name)
            if booth:
                index_booths.add(booth)

        extracted_names = set()
        extracted_booths = set()

        for company in extracted_companies:
            name = company.get('company_name_en', '').strip().lower()
            booth = company.get('booth_number', '').strip()

            if name:
                extracted_names.add(name)
            if booth:
                extracted_booths.add(booth)

        # Find missing and extra companies
        missing_names = index_names - extracted_names
        extra_names = extracted_names - index_names
        missing_booths = index_booths - extracted_booths

        # Try to match missing companies by partial name match
        matched_missing = []
        still_missing = []

        for missing_name in missing_names:
            # Check if any extracted name contains this name (or vice versa)
            found_match = False
            for extracted_name in extracted_names:
                if (missing_name in extracted_name or
                    extracted_name in missing_name or
                    self._similarity_score(missing_name, extracted_name) > 0.8):
                    matched_missing.append({
                        'index_name': missing_name,
                        'extracted_name': extracted_name,
                        'match_type': 'partial'
                    })
                    found_match = True
                    break

            if not found_match:
                still_missing.append(missing_name)

        # Generate report
        report = {
            'index_total': len(index_companies),
            'extracted_total': len(extracted_companies),
            'index_unique_names': len(index_names),
            'extracted_unique_names': len(extracted_names),
            'missing_companies_count': len(still_missing),
            'missing_companies': sorted(still_missing),
            'partial_matches_count': len(matched_missing),
            'partial_matches': matched_missing,
            'extra_companies_count': len(extra_names),
            'missing_booths_count': len(missing_booths),
            'missing_booths': sorted(missing_booths),
            'coverage_percentage': round(
                (len(extracted_names) / len(index_names) * 100) if index_names else 0,
                2
            )
        }

        return report

    def _similarity_score(self, str1: str, str2: str) -> float:
        """Calculate simple similarity score between two strings"""
        # Jaccard similarity on words
        words1 = set(str1.split())
        words2 = set(str2.split())

        if not words1 or not words2:
            return 0.0

        intersection = words1 & words2
        union = words1 | words2

        return len(intersection) / len(union)

    def print_comparison_report(self, report: Dict):
        """Print formatted comparison report"""
        logger.info("\n" + "=" * 70)
        logger.info("VERIFICATION REPORT")
        logger.info("=" * 70)
        logger.info(f"\nIndex Statistics:")
        logger.info(f"  Total entries in index: {report['index_total']}")
        logger.info(f"  Unique company names: {report['index_unique_names']}")

        logger.info(f"\nExtraction Statistics:")
        logger.info(f"  Total companies extracted: {report['extracted_total']}")
        logger.info(f"  Unique company names: {report['extracted_unique_names']}")

        logger.info(f"\nCoverage:")
        logger.info(f"  ✅ Coverage: {report['coverage_percentage']}%")

        logger.info(f"\nMissing Companies:")
        logger.info(f"  Total missing: {report['missing_companies_count']}")
        if report['missing_companies_count'] > 0:
            logger.info(f"  First 20 missing:")
            for name in report['missing_companies'][:20]:
                logger.info(f"    - {name}")

        logger.info(f"\nPartial Matches:")
        logger.info(f"  Total partial matches: {report['partial_matches_count']}")
        if report['partial_matches_count'] > 0:
            logger.info(f"  First 10 partial matches:")
            for match in report['partial_matches'][:10]:
                logger.info(f"    Index: {match['index_name']}")
                logger.info(f"    Found: {match['extracted_name']}")
                logger.info("")

        logger.info(f"\nMissing Booth Numbers:")
        logger.info(f"  Total missing: {report['missing_booths_count']}")
        if report['missing_booths_count'] > 0:
            logger.info(f"  First 20 missing booths:")
            for booth in report['missing_booths'][:20]:
                logger.info(f"    - {booth}")


async def main():
    """Main verification workflow"""
    verifier = CompanyIndexVerifier()

    try:
        # Step 1: OCR index pages
        logger.info("Step 1: Extracting index pages (77-129)")
        index_texts = await verifier.extract_index_pages(start_page=77, end_page=129)

        # Save raw index OCR
        index_ocr_file = verifier.config.get_full_path('data/index_ocr_raw.json')
        with open(index_ocr_file, 'w', encoding='utf-8') as f:
            json.dump({
                'extracted_at': datetime.now().isoformat(),
                'pages': index_texts,
                'page_range': '77-129'
            }, f, indent=2, ensure_ascii=False)
        logger.info(f"✅ Saved raw index OCR to {index_ocr_file}")

        # Step 2: Parse company names from index
        logger.info("\nStep 2: Parsing company names from index")
        index_companies = verifier.parse_index_companies(index_texts)

        # Save parsed index companies
        index_companies_file = verifier.config.get_full_path('data/index_companies.json')
        with open(index_companies_file, 'w', encoding='utf-8') as f:
            json.dump({
                'extracted_at': datetime.now().isoformat(),
                'total_companies': len(index_companies),
                'companies': index_companies
            }, f, indent=2, ensure_ascii=False)
        logger.info(f"✅ Saved index companies to {index_companies_file}")

        # Step 3: Load extracted companies
        logger.info("\nStep 3: Loading extracted companies for comparison")
        structured_file = verifier.config.get_full_path('data/structured_companies.json')

        with open(structured_file, 'r', encoding='utf-8') as f:
            structured_data = json.load(f)
            extracted_companies = structured_data.get('companies', [])

        logger.info(f"Loaded {len(extracted_companies)} extracted companies")

        # Step 4: Compare
        logger.info("\nStep 4: Comparing index with extracted companies")
        comparison_report = verifier.compare_with_extracted(
            index_companies,
            extracted_companies
        )

        # Save comparison report
        report_file = verifier.config.get_full_path('data/index_verification_report.json')
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump({
                'verified_at': datetime.now().isoformat(),
                'report': comparison_report
            }, f, indent=2, ensure_ascii=False)
        logger.info(f"✅ Saved verification report to {report_file}")

        # Print report
        verifier.print_comparison_report(comparison_report)

        logger.info("\n✅ Verification complete!")

    except Exception as e:
        logger.error(f"\n❌ Error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise


if __name__ == "__main__":
    asyncio.run(main())
