#!/usr/bin/env python3
"""
Compare Index Companies

Compares companies from the index (pages 77-129) with extracted companies
to find missing entries.
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Set

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def normalize_name(name: str) -> str:
    """Normalize company name for comparison"""
    if not name:
        return ""
    # Convert to lowercase and remove extra spaces
    name = name.lower().strip()
    # Remove common suffixes for better matching
    for suffix in [' co., ltd', ' co ltd', ' company', ' corp', ' inc', ' limited']:
        if name.endswith(suffix):
            name = name[:-len(suffix)].strip()
    return name


def load_index_companies(index_ocr_file: str) -> List[Dict]:
    """Load and parse companies from index OCR"""
    logger.info(f"Loading index OCR from {index_ocr_file}")
    import re

    with open(index_ocr_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    companies = []

    # Process each page
    for page in data.get('pages', []):
        text = page.get('text', '')
        if not text:
            continue

        # Check if Gemini returned JSON format (first page)
        if '```json' in text or text.strip().startswith('['):
            try:
                # Extract JSON from markdown code block
                json_text = text
                if '```json' in text:
                    json_text = re.search(r'```json\n(.*?)\n```', text, re.DOTALL)
                    if json_text:
                        json_text = json_text.group(1)
                elif '```' in text:
                    json_text = re.search(r'```\n?(.*?)\n?```', text, re.DOTALL)
                    if json_text:
                        json_text = json_text.group(1)

                # Parse JSON
                page_companies = json.loads(json_text)
                for company in page_companies:
                    name_en = company.get('company_name_english')
                    name_zh = company.get('company_name_chinese')
                    booth = company.get('booth_number')

                    # Use English name if available, otherwise Chinese
                    name = name_en if name_en else name_zh

                    if name and booth:
                        companies.append({
                            'name': name,
                            'booth': booth,
                            'normalized': normalize_name(name)
                        })
            except Exception as e:
                logger.warning(f"Failed to parse JSON from page: {e}")
                # Fall back to text parsing
                pass

        # Parse plain text format (most pages)
        # Format: Chinese Name.......Booth#.......Page#
        #         English Name
        lines = text.split('\n')
        for i, line in enumerate(lines):
            line = line.strip()
            if len(line) < 15:
                continue

            # Look for booth number pattern
            booth_matches = re.findall(r'\b(\d+\.\d+[A-Z]+\d+(?:,\d+\.\d+[A-Z]+\d+)*)\b', line)

            if booth_matches:
                booth = booth_matches[0]

                # Extract company name before booth number
                # Split by dots (Chinese companies use ....... before booth)
                name_part = re.split(r'\.{2,}', line)[0].strip()

                # Check if this is Chinese or English name
                has_chinese = bool(re.search(r'[\u4e00-\u9fff]', name_part))

                if has_chinese:
                    # Chinese name - check next line for English name
                    chinese_name = name_part
                    english_name = None

                    if i + 1 < len(lines):
                        next_line = lines[i + 1].strip()
                        # English name should not have booth number and should be capitalized
                        if not re.search(r'\d+\.\d+[A-Z]+\d+', next_line) and re.search(r'^[A-Z]', next_line):
                            english_name = next_line.strip()

                    # Use English name if available, otherwise Chinese
                    name = english_name if english_name else chinese_name

                    companies.append({
                        'name': name,
                        'name_en': english_name,
                        'name_zh': chinese_name,
                        'booth': booth,
                        'normalized': normalize_name(name)
                    })
                else:
                    # English name only
                    name = name_part
                    companies.append({
                        'name': name,
                        'name_en': name,
                        'name_zh': None,
                        'booth': booth,
                        'normalized': normalize_name(name)
                    })

    logger.info(f"Parsed {len(companies)} companies from index")
    return companies


def load_extracted_companies(structured_file: str) -> List[Dict]:
    """Load extracted companies from step 2"""
    logger.info(f"Loading extracted companies from {structured_file}")

    with open(structured_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    companies = []
    for company in data.get('companies', []):
        name = company.get('company_name_en', '')
        booth = company.get('booth_number', '')

        companies.append({
            'name': name,
            'booth': booth,
            'normalized': normalize_name(name),
            'data': company
        })

    logger.info(f"Loaded {len(companies)} extracted companies")
    return companies


def compare_companies(index_companies: List[Dict], extracted_companies: List[Dict]) -> Dict:
    """Compare index with extracted companies"""
    logger.info("\nComparing companies...")

    # Create sets for comparison
    index_names = {c['normalized'] for c in index_companies if c['normalized']}
    extracted_names = {c['normalized'] for c in extracted_companies if c['normalized']}

    index_booths = {c['booth'] for c in index_companies if c['booth']}
    extracted_booths = {c['booth'] for c in extracted_companies if c['booth']}

    # Find missing
    missing_names = index_names - extracted_names
    missing_booths = index_booths - extracted_booths

    # Find missing companies with details
    missing_companies = []
    for company in index_companies:
        if company['normalized'] in missing_names:
            missing_companies.append(company)

    # Find companies by booth that might be partial matches
    booth_matches = []
    for missing in missing_companies[:]:
        for extracted in extracted_companies:
            if missing['booth'] == extracted['booth']:
                booth_matches.append({
                    'index_name': missing['name'],
                    'extracted_name': extracted['name'],
                    'booth': missing['booth']
                })
                missing_companies.remove(missing)
                break

    return {
        'index_total': len(index_companies),
        'extracted_total': len(extracted_companies),
        'index_unique_names': len(index_names),
        'extracted_unique_names': len(extracted_names),
        'missing_count': len(missing_companies),
        'missing_companies': missing_companies,
        'booth_matches': booth_matches,
        'missing_booths': sorted(missing_booths),
        'coverage': round(len(extracted_names) / len(index_names) * 100, 2) if index_names else 0
    }


def print_report(report: Dict):
    """Print comparison report"""
    print("\n" + "=" * 70)
    print("INDEX VERIFICATION REPORT")
    print("=" * 70)

    print(f"\nIndex: {report['index_total']} companies ({report['index_unique_names']} unique)")
    print(f"Extracted: {report['extracted_total']} companies ({report['extracted_unique_names']} unique)")
    print(f"\nCoverage: {report['coverage']}%")

    print(f"\nMissing companies: {report['missing_count']}")
    if report['missing_companies']:
        print("\nFirst 30 missing companies:")
        for i, company in enumerate(report['missing_companies'][:30], 1):
            print(f"  {i}. {company['name']} (Booth: {company['booth']})")

    print(f"\nBooth matches (different names): {len(report['booth_matches'])}")
    if report['booth_matches']:
        print("\nFirst 20 booth matches:")
        for i, match in enumerate(report['booth_matches'][:20], 1):
            print(f"  {i}. Booth {match['booth']}:")
            print(f"     Index:     {match['index_name']}")
            print(f"     Extracted: {match['extracted_name']}")


def main():
    """Main comparison"""
    base_dir = Path('/Users/gabrielreginatto/Desktop/Code/Medical/CMEF')

    # File paths
    index_ocr_file = base_dir / 'data/ocr_raw_output.json'
    structured_file = base_dir / 'data/structured_companies.json'

    # Load data
    index_companies = load_index_companies(str(index_ocr_file))
    extracted_companies = load_extracted_companies(str(structured_file))

    # Compare
    report = compare_companies(index_companies, extracted_companies)

    # Save report
    report_file = base_dir / 'data/index_comparison_report.json'
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    logger.info(f"\n✅ Saved report to {report_file}")

    # Print report
    print_report(report)


if __name__ == "__main__":
    main()
