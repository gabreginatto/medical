"""
Data Validator

Validates and cleans extracted company data.
"""

import logging
import re
import asyncio
import aiohttp
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import CMEFConfig, DEFAULT_CONFIG, REGEX_PATTERNS

logger = logging.getLogger(__name__)


class DataValidator:
    """Validates and cleans CMEF company data"""

    def __init__(self, config: CMEFConfig = DEFAULT_CONFIG):
        """
        Initialize validator

        Args:
            config: CMEF configuration object
        """
        self.config = config
        self.validation_results = []

    def validate_company(self, company: Dict) -> Tuple[Dict, List[str]]:
        """
        Validate all fields in a company record

        Args:
            company: Company data dictionary

        Returns:
            Tuple of (validated_company, list_of_issues)
        """
        issues = []
        validated = company.copy()

        # Validate company name
        if not company.get('company_name_en'):
            issues.append("Missing English company name")
        else:
            validated['company_name_en'] = self.clean_company_name(company['company_name_en'])

        # Validate email
        if company.get('email'):
            if not self.validate_email(company['email']):
                issues.append(f"Invalid email format: {company['email']}")
            else:
                validated['email'] = company['email'].lower().strip()

        # Validate website
        if company.get('website'):
            cleaned_url = self.clean_website_url(company['website'])
            if cleaned_url:
                validated['website'] = cleaned_url
            else:
                issues.append(f"Invalid website URL: {company['website']}")

        # Validate booth number
        if company.get('booth_number'):
            if not self.validate_booth_number(company['booth_number']):
                issues.append(f"Invalid booth number format: {company['booth_number']}")

        # Validate NCM code
        if company.get('ncm_code'):
            if not self.validate_ncm_code(company['ncm_code']):
                issues.append(f"Invalid NCM code format: {company['ncm_code']}")

        # Validate risk class
        if company.get('risk_class'):
            if company['risk_class'] not in ["I", "II", "III", "Unknown"]:
                issues.append(f"Invalid risk class: {company['risk_class']}")

        return validated, issues

    def validate_email(self, email: str) -> bool:
        """
        Validate email format

        Args:
            email: Email address string

        Returns:
            True if valid format
        """
        if not email:
            return False

        pattern = r'^[\w\.\-]+@[\w\.\-]+\.\w+$'
        return bool(re.match(pattern, email, re.IGNORECASE))

    def clean_website_url(self, url: str) -> Optional[str]:
        """
        Clean and validate website URL

        Args:
            url: Website URL string

        Returns:
            Cleaned URL or None if invalid
        """
        if not url:
            return None

        url = url.strip()

        # Remove common OCR artifacts
        url = url.replace(' ', '')
        url = url.replace(',', '.')

        # Add protocol if missing
        if not url.startswith(('http://', 'https://')):
            url = 'http://' + url

        # Basic URL validation
        try:
            parsed = urlparse(url)
            if parsed.netloc and '.' in parsed.netloc:
                return url
        except Exception:
            pass

        return None

    def validate_booth_number(self, booth: str) -> bool:
        """
        Validate booth number format

        Expected format: X.XAXX (e.g., "6.1A05")

        Args:
            booth: Booth number string

        Returns:
            True if valid format
        """
        if not booth:
            return False

        pattern = r'^\d+\.\d+[A-Z]\d+$'
        return bool(re.match(pattern, booth))

    def validate_ncm_code(self, ncm: str) -> bool:
        """
        Validate NCM code format

        Expected format: XXXX.XX.XX

        Args:
            ncm: NCM code string

        Returns:
            True if valid format
        """
        if not ncm:
            return False

        pattern = r'^\d{4}\.\d{2}\.\d{2}$'
        return bool(re.match(pattern, ncm))

    def clean_company_name(self, name: str) -> str:
        """
        Clean and standardize company name

        Args:
            name: Company name string

        Returns:
            Cleaned company name
        """
        if not name:
            return ""

        # Remove extra whitespace
        name = ' '.join(name.split())

        # Standardize common abbreviations
        replacements = {
            r'\bCo\s*Ltd\b': 'Co., Ltd.',
            r'\bCo\.,?\s*Limited\b': 'Co., Ltd.',
            r'\bCorporation\b': 'Corp.',
            r'\bIncorporated\b': 'Inc.',
        }

        for pattern, replacement in replacements.items():
            name = re.sub(pattern, replacement, name, flags=re.IGNORECASE)

        return name.strip()

    async def validate_website_online(self, url: str) -> Tuple[bool, int, str]:
        """
        Check if website is accessible online

        Args:
            url: Website URL

        Returns:
            Tuple of (is_accessible, status_code, error_message)
        """
        if not url:
            return False, 0, "No URL provided"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.head(
                    url,
                    timeout=aiohttp.ClientTimeout(total=self.config.WEBSITE_TIMEOUT),
                    allow_redirects=True
                ) as response:
                    if response.status < 400:
                        return True, response.status, ""
                    else:
                        return False, response.status, f"HTTP {response.status}"

        except asyncio.TimeoutError:
            return False, 0, "Timeout"
        except aiohttp.ClientError as e:
            return False, 0, str(e)
        except Exception as e:
            return False, 0, f"Error: {e}"

    async def validate_websites_batch(self, companies: List[Dict]) -> List[Dict]:
        """
        Validate website accessibility for a batch of companies

        Args:
            companies: List of company dictionaries

        Returns:
            List of companies with website_validated field added
        """
        logger.info(f"Validating websites for {len(companies)} companies")

        # Create validation tasks
        tasks = []
        for company in companies:
            url = company.get('website')
            if url:
                task = self.validate_website_online(url)
                tasks.append((company, task))
            else:
                company['website_validated'] = False
                company['website_status'] = "No URL"

        # Run validations with concurrency limit
        semaphore = asyncio.Semaphore(self.config.MAX_CONCURRENT_VALIDATIONS)

        async def validate_with_semaphore(company, task):
            async with semaphore:
                is_valid, status_code, error_msg = await task
                company['website_validated'] = is_valid
                company['website_status_code'] = status_code
                company['website_error'] = error_msg
                return company

        validated_tasks = [
            validate_with_semaphore(company, task)
            for company, task in tasks
        ]

        await asyncio.gather(*validated_tasks)

        # Log results
        valid_count = sum(1 for c in companies if c.get('website_validated'))
        logger.info(f"Website validation complete: {valid_count}/{len(companies)} accessible")

        return companies

    def generate_validation_report(self, companies: List[Dict]) -> Dict:
        """
        Generate validation report

        Args:
            companies: List of validated company dictionaries

        Returns:
            Validation report dictionary
        """
        total = len(companies)
        issues_by_type = {
            'missing_email': 0,
            'missing_website': 0,
            'missing_address': 0,
            'invalid_email': 0,
            'invalid_website': 0,
            'invalid_booth': 0,
            'website_unreachable': 0,
            'high_risk_incomplete': 0  # Class III companies missing critical data
        }

        high_risk_issues = []

        for company in companies:
            # Check for missing fields
            if not company.get('email'):
                issues_by_type['missing_email'] += 1

            if not company.get('website'):
                issues_by_type['missing_website'] += 1

            if not company.get('address'):
                issues_by_type['missing_address'] += 1

            # Check invalid fields
            if company.get('email') and not self.validate_email(company['email']):
                issues_by_type['invalid_email'] += 1

            if company.get('website') and not self.clean_website_url(company['website']):
                issues_by_type['invalid_website'] += 1

            if company.get('booth_number') and not self.validate_booth_number(company['booth_number']):
                issues_by_type['invalid_booth'] += 1

            # Check website accessibility
            if not company.get('website_validated'):
                issues_by_type['website_unreachable'] += 1

            # High-risk companies (Class III) with incomplete data
            if company.get('risk_class') == 'III':
                missing_fields = []
                if not company.get('email'):
                    missing_fields.append('email')
                if not company.get('website'):
                    missing_fields.append('website')
                if not company.get('address'):
                    missing_fields.append('address')

                if missing_fields:
                    issues_by_type['high_risk_incomplete'] += 1
                    high_risk_issues.append({
                        'company_name': company.get('company_name_en', 'Unknown'),
                        'missing_fields': missing_fields
                    })

        report = {
            'total_companies': total,
            'issues_summary': issues_by_type,
            'data_completeness': {
                'email': (total - issues_by_type['missing_email']) / total * 100 if total else 0,
                'website': (total - issues_by_type['missing_website']) / total * 100 if total else 0,
                'address': (total - issues_by_type['missing_address']) / total * 100 if total else 0,
            },
            'high_risk_issues': high_risk_issues
        }

        return report

    def print_validation_report(self, report: Dict):
        """Print validation report to logger"""
        logger.info("\n" + "=" * 70)
        logger.info("DATA VALIDATION REPORT")
        logger.info("=" * 70)

        logger.info(f"\nTotal Companies: {report['total_companies']}")

        logger.info("\nIssues Summary:")
        for issue_type, count in report['issues_summary'].items():
            percentage = (count / report['total_companies']) * 100 if report['total_companies'] else 0
            logger.info(f"  {issue_type}: {count} ({percentage:.1f}%)")

        logger.info("\nData Completeness:")
        for field, percentage in report['data_completeness'].items():
            logger.info(f"  {field}: {percentage:.1f}%")

        if report['high_risk_issues']:
            logger.info(f"\nHigh-Risk Companies with Incomplete Data ({len(report['high_risk_issues'])}):")
            for issue in report['high_risk_issues'][:10]:  # Show first 10
                logger.info(f"  - {issue['company_name']}: missing {', '.join(issue['missing_fields'])}")


__all__ = ['DataValidator']
