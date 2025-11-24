"""
Gemini Parser Client

Uses Gemini 2.5 Flash for intelligent parsing and classification of OCR text.
"""

import asyncio
import json
import logging
import os
import time
from typing import List, Dict, Optional
import re

try:
    import google.generativeai as genai
except ImportError:
    raise ImportError(
        "Missing required library: google-generativeai. "
        "Install with: pip install google-generativeai"
    )

from dotenv import load_dotenv
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import CMEFConfig, DEFAULT_CONFIG, REGEX_PATTERNS

load_dotenv()
logger = logging.getLogger(__name__)


class GeminiParserClient:
    """Client for parsing and structuring CMEF data using Gemini"""

    def __init__(self, config: CMEFConfig = DEFAULT_CONFIG):
        """
        Initialize Gemini client

        Args:
            config: CMEF configuration object
        """
        self.config = config
        self._initialize_gemini()

    def _initialize_gemini(self):
        """Initialize Gemini API"""
        logger.info("Initializing Gemini API client")

        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in .env file")

        genai.configure(api_key=api_key)

        # Try to use Gemini 2.0 Flash, fallback to 1.5 Flash
        try:
            self.model = genai.GenerativeModel(self.config.GEMINI_MODEL)
            logger.info(f"Initialized Gemini model: {self.config.GEMINI_MODEL}")
        except Exception as e:
            logger.warning(f"Failed to load {self.config.GEMINI_MODEL}: {e}")
            logger.info(f"Falling back to {self.config.GEMINI_FALLBACK_MODEL}")
            self.model = genai.GenerativeModel(self.config.GEMINI_FALLBACK_MODEL)

    def parse_company_data(self, ocr_text: str) -> Dict:
        """
        Parse company information from OCR text using Gemini

        Args:
            ocr_text: Raw OCR text from one or more pages

        Returns:
            Dictionary with structured company data
        """
        logger.debug(f"Parsing OCR text ({len(ocr_text)} characters)")

        prompt = self._create_parsing_prompt(ocr_text)

        try:
            response = self.model.generate_content(prompt)
            response_text = response.text.strip()

            # Clean markdown code blocks if present
            if response_text.startswith('```'):
                lines = response_text.split('\n')
                response_text = '\n'.join(
                    line for line in lines
                    if not line.strip().startswith('```')
                )

            # Parse JSON
            company_data = json.loads(response_text)

            # Apply regex fallbacks for missing fields
            company_data = self._apply_regex_fallbacks(company_data, ocr_text)

            return company_data

        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error: {e}")
            logger.debug(f"Response text: {response_text[:500]}...")

            # Fallback to pure regex extraction
            return self._fallback_regex_extraction(ocr_text)

        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            return self._fallback_regex_extraction(ocr_text)

    def parse_company_batch(self, ocr_texts: List[str]) -> List[Dict]:
        """
        Parse multiple companies in a single API call (batch processing)

        Args:
            ocr_texts: List of OCR text blocks

        Returns:
            List of parsed company data dictionaries
        """
        logger.info(f"Parsing batch of {len(ocr_texts)} companies")

        prompt = self._create_batch_parsing_prompt(ocr_texts)

        try:
            response = self.model.generate_content(prompt)
            response_text = response.text.strip()

            # Clean markdown
            if response_text.startswith('```'):
                lines = response_text.split('\n')
                response_text = '\n'.join(
                    line for line in lines
                    if not line.strip().startswith('```')
                )

            # Parse JSON array
            companies = json.loads(response_text)

            logger.info(f"Successfully parsed {len(companies)} companies")
            return companies

        except Exception as e:
            logger.error(f"Batch parsing error: {e}")
            # Fallback to individual parsing
            logger.info("Falling back to individual parsing")
            return [self.parse_company_data(text) for text in ocr_texts]

    def classify_product_category(self, scope_description: str) -> Dict:
        """
        Classify product category from scope description

        Args:
            scope_description: Product/scope description text

        Returns:
            Dictionary with:
            {
                'category': str,
                'product_keywords': list,
                'confidence': float
            }
        """
        prompt = f"""Analyze this medical equipment company's product description and classify it.

**Description:**
{scope_description}

**Available Categories:**
- Cardiology & Cardiovascular
- Orthopedics & Rehabilitation
- Radiology & Imaging Equipment
- Surgical Instruments & Tools
- Laboratory & Diagnostics
- Critical Care & Monitoring
- Respiratory Care
- Obstetrics & Gynecology
- Dentistry & Oral Care
- Ophthalmology Equipment
- Neurology & Neurosurgery
- Hospital Furniture & Infrastructure
- Disposable Medical Supplies
- Sterilization & Disinfection
- Emergency & Rescue Equipment
- Other Medical Equipment

**Output JSON format:**
{{
  "category": "Primary category (choose ONE from list above)",
  "product_keywords": ["keyword1", "keyword2", "keyword3"],
  "confidence": 0.95
}}

**Instructions:**
- Choose the SINGLE most appropriate category
- Extract 3-7 specific product keywords from the description
- Keywords should be searchable terms (e.g., "hospital bed", "ultrasound", "surgical scissors")
- Confidence between 0.0-1.0
- Return ONLY the JSON, no other text"""

        try:
            response = self.model.generate_content(prompt)
            response_text = response.text.strip()

            # Clean markdown
            if '```' in response_text:
                response_text = re.sub(r'```(?:json)?\n?', '', response_text)

            return json.loads(response_text)

        except Exception as e:
            logger.error(f"Category classification error: {e}")
            return {
                'category': 'Other Medical Equipment',
                'product_keywords': [],
                'confidence': 0.0
            }

    def _create_parsing_prompt(self, ocr_text: str) -> str:
        """Create prompt for parsing single company data"""
        return f"""Extract structured company information from this OCR text from a Chinese medical equipment catalog (CMEF 2025).

**OCR Text:**
{ocr_text[:3000]}

**Extract ONLY these fields (do not infer or add anything not explicitly in the text):**
- company_name_en: English company name
- company_name_zh: Chinese company name (if present)
- booth_number: Exhibition booth number (format: X.XAXX like "8.1F11")
- address: Full address (as written)
- email: Email address
- website: Website URL
- phone: Phone number
- scope_description: Product scope/description (preserve original text)

**Output JSON format:**
{{
  "company_name_en": "...",
  "company_name_zh": "...",
  "booth_number": "...",
  "address": "...",
  "email": "...",
  "website": "...",
  "phone": "...",
  "scope_description": "..."
}}

**Rules:**
- Use null for missing fields (do NOT invent data)
- Clean up obvious OCR errors in text
- Standardize company name format (e.g., "Co., Ltd" not "Co Ltd")
- Ensure website starts with http:// or https://
- Keep scope_description as-is from the catalog (do not summarize or interpret)
- Return ONLY the JSON, no other text"""

    def _create_batch_parsing_prompt(self, ocr_texts: List[str]) -> str:
        """Create prompt for parsing multiple PAGES (each with 6 companies)"""
        # Each OCR text is a full page with 6 companies
        # Don't truncate too much - we need all company data
        texts_formatted = "\n\n===== PAGE BREAK =====\n\n".join(
            f"PAGE {i+1}:\n{text[:5000]}"  # Increased from 1000 to 5000 chars
            for i, text in enumerate(ocr_texts)
        )

        return f"""Extract ALL company information from these catalog pages. Each page contains EXACTLY 6 company entries arranged in a 2x3 grid.

**IMPORTANT:** You MUST extract ALL 6 companies from EACH page.

**OCR Text from {len(ocr_texts)} pages:**
{texts_formatted}

**For EACH of the 6 companies on EACH page, extract:**
- company_name_en: English company name
- company_name_zh: Chinese company name
- booth_number: Exhibition booth number
- address: Full address
- email: Email address
- website: Website URL
- phone: Phone number
- scope_description: Product scope/description

**Output JSON array format (ALL companies from ALL pages):**
[
  {{
    "company_name_en": "...",
    "company_name_zh": "...",
    "booth_number": "...",
    "address": "...",
    "email": "...",
    "website": "...",
    "phone": "...",
    "scope_description": "..."
  }},
  ... (repeat for ALL 6 companies on EACH page = {len(ocr_texts) * 6} total companies)
]

**Rules:**
- Extract ALL {len(ocr_texts) * 6} companies (6 per page × {len(ocr_texts)} pages)
- Use null for missing fields
- Return ONLY the JSON array, no other text"""

    def _apply_regex_fallbacks(self, company_data: Dict, ocr_text: str) -> Dict:
        """Apply regex patterns to fill in missing fields"""

        # Email fallback
        if not company_data.get('email'):
            emails = re.findall(REGEX_PATTERNS['email'], ocr_text, re.IGNORECASE)
            if emails:
                company_data['email'] = emails[0]

        # Website fallback
        if not company_data.get('website'):
            websites = re.findall(REGEX_PATTERNS['website'], ocr_text, re.IGNORECASE)
            if websites:
                website = websites[0]
                if not website.startswith('http'):
                    website = 'http://' + website
                company_data['website'] = website

        # Booth number fallback
        if not company_data.get('booth_number'):
            booths = re.findall(REGEX_PATTERNS['booth_number'], ocr_text)
            if booths:
                company_data['booth_number'] = booths[0]

        return company_data

    def _fallback_regex_extraction(self, ocr_text: str) -> Dict:
        """Pure regex-based extraction as fallback"""
        logger.warning("Using fallback regex extraction")

        return {
            'company_name_en': self._extract_company_name(ocr_text),
            'company_name_zh': None,
            'booth_number': self._extract_booth_number(ocr_text),
            'address': None,
            'email': self._extract_email(ocr_text),
            'website': self._extract_website(ocr_text),
            'phone': self._extract_phone(ocr_text),
            'scope_description': ocr_text[:500]  # First 500 chars
        }

    def _extract_company_name(self, text: str) -> Optional[str]:
        """Extract company name (simple heuristic)"""
        # Look for "Co., Ltd" or "Company"
        patterns = [
            r'([A-Z][A-Za-z\s&]+(?:Co\.,?\s*Ltd\.?|Company|Corp\.?))',
            r'^([A-Z][A-Za-z\s&]+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.MULTILINE)
            if match:
                return match.group(1).strip()
        return None

    def _extract_booth_number(self, text: str) -> Optional[str]:
        """Extract booth number"""
        match = re.search(REGEX_PATTERNS['booth_number'], text)
        return match.group(0) if match else None

    def _extract_email(self, text: str) -> Optional[str]:
        """Extract email"""
        match = re.search(REGEX_PATTERNS['email'], text, re.IGNORECASE)
        return match.group(0) if match else None

    def _extract_website(self, text: str) -> Optional[str]:
        """Extract website"""
        match = re.search(REGEX_PATTERNS['website'], text, re.IGNORECASE)
        if match:
            website = match.group(0)
            if not website.startswith('http'):
                website = 'http://' + website
            return website
        return None

    def _extract_phone(self, text: str) -> Optional[str]:
        """Extract phone number"""
        match = re.search(REGEX_PATTERNS['phone'], text)
        return match.group(0) if match else None


# ==================== ASYNC BATCH PROCESSOR ====================

class AsyncGeminiProcessor:
    """Async wrapper for batch processing with rate limiting"""

    def __init__(self, config: CMEFConfig = DEFAULT_CONFIG):
        """Initialize async processor"""
        self.client = GeminiParserClient(config)
        self.config = config
        self.last_request_time = 0

    async def process_batch_with_rate_limit(self, ocr_texts: List[str]) -> List[Dict]:
        """Process batch with rate limiting"""
        # Rate limiting
        elapsed = time.time() - self.last_request_time
        if elapsed < self.config.GEMINI_REQUEST_DELAY:
            await asyncio.sleep(self.config.GEMINI_REQUEST_DELAY - elapsed)

        self.last_request_time = time.time()

        # Process batch
        results = self.client.parse_company_batch(ocr_texts)

        return results

    async def process_all_batches(self, all_ocr_texts: List[str]) -> List[Dict]:
        """Process all OCR texts in batches with rate limiting"""
        batch_size = self.config.GEMINI_BATCH_SIZE
        all_results = []

        num_batches = (len(all_ocr_texts) + batch_size - 1) // batch_size

        logger.info(f"Processing {len(all_ocr_texts)} companies in {num_batches} batches")

        for i in range(0, len(all_ocr_texts), batch_size):
            batch_num = i // batch_size + 1
            batch = all_ocr_texts[i:i + batch_size]

            logger.info(f"Processing batch {batch_num}/{num_batches}")

            results = await self.process_batch_with_rate_limit(batch)
            all_results.extend(results)

        return all_results


__all__ = ['GeminiParserClient', 'AsyncGeminiProcessor']
