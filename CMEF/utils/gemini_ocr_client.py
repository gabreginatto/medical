"""
Gemini OCR Client

Handles OCR extraction using Gemini 2.5 Flash Lite via Vertex AI.
Superior quality compared to DeepSeek for complex Chinese/English documents.
"""

import logging
import time
from typing import List, Dict, Optional
from pathlib import Path

try:
    import vertexai
    from vertexai.generative_models import GenerativeModel, Part
except ImportError:
    raise ImportError(
        "Missing required library: vertexai. "
        "Install with: pip install google-cloud-aiplatform"
    )

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import CMEFConfig, DEFAULT_CONFIG

logger = logging.getLogger(__name__)


class GeminiOCRClient:
    """Client for Gemini 2.5 Flash Lite OCR via Vertex AI"""

    def __init__(self, config: CMEFConfig = DEFAULT_CONFIG):
        """
        Initialize Gemini OCR client

        Args:
            config: CMEF configuration object
        """
        self.config = config
        self.model_name = "gemini-2.5-flash-lite"

        # Initialize Vertex AI - remove old credentials env var
        import os
        if 'GOOGLE_APPLICATION_CREDENTIALS' in os.environ:
            del os.environ['GOOGLE_APPLICATION_CREDENTIALS']

        # Use gcloud user credentials
        vertexai.init(
            project=config.DEEPSEEK_PROJECT_ID,  # Reuse project ID
            location="us-central1"
        )

        # Initialize Gemini model
        self.model = GenerativeModel(self.model_name)

        logger.info(f"✅ Initialized Gemini OCR client with model: {self.model_name}")

    def extract_text_from_image(self, image_path: str, retry_count: int = 0) -> Dict:
        """
        Extract text from a single image using Gemini 2.5 Flash Lite

        Args:
            image_path: Path to image file
            retry_count: Current retry attempt

        Returns:
            Dictionary with OCR results:
            {
                'image_path': str,
                'text': str,
                'confidence': float,
                'metadata': dict
            }
        """
        logger.debug(f"Processing image: {Path(image_path).name}")

        try:
            # Read image bytes
            with open(image_path, 'rb') as f:
                image_bytes = f.read()

            # Create image part
            image_part = Part.from_data(image_bytes, mime_type="image/png")

            # OCR prompt - optimized for catalog pages with 6 companies per page
            prompt = """Extract all text from this page from a Chinese medical equipment trade show catalog.

IMPORTANT: This page contains EXACTLY 6 company entries arranged in a 2x3 grid (2 columns, 3 rows).
You MUST extract all 6 companies.

For each company, extract:
- Company name (Chinese and English)
- Booth number
- Address
- Contact information (email, phone, website)
- Product descriptions

Please output the text accurately, preserving the layout structure.
Make sure you capture ALL 6 companies on this page."""

            # Generate content
            response = self.model.generate_content([prompt, image_part])

            ocr_text = response.text

            # Validate: Count number of companies extracted
            company_count = self._count_companies_in_text(ocr_text)

            # If we didn't get 6 companies, retry with more explicit prompt
            if company_count < 6 and retry_count == 0:
                logger.warning(f"Only found {company_count} companies on {Path(image_path).name}, expected 6. Retrying with enhanced prompt...")
                return self._extract_with_structured_prompt(image_path, retry_count + 1)

            ocr_result = {
                'image_path': image_path,
                'text': ocr_text,
                'confidence': 0.95,  # Gemini doesn't provide confidence, assume high quality
                'metadata': {
                    'page': self._extract_page_number(image_path),
                    'timestamp': time.time(),
                    'model': self.model_name,
                    'char_count': len(ocr_text),
                    'companies_detected': company_count,
                    'validation_passed': company_count >= 6
                }
            }

            if company_count < 6:
                logger.warning(f"⚠️ Page {Path(image_path).name}: Only captured {company_count}/6 companies")
            else:
                logger.debug(f"✅ Extracted {company_count} companies, {len(ocr_text)} characters")

            return ocr_result

        except Exception as e:
            logger.error(f"Gemini OCR failed for {image_path}: {e}")

            # Retry logic
            if retry_count < self.config.OCR_MAX_RETRIES:
                logger.info(f"Retrying... (attempt {retry_count + 1}/{self.config.OCR_MAX_RETRIES})")
                time.sleep(self.config.OCR_RETRY_DELAY)
                return self.extract_text_from_image(image_path, retry_count + 1)
            else:
                # Return error result
                return {
                    'image_path': image_path,
                    'text': '',
                    'confidence': 0.0,
                    'metadata': {'error': str(e), 'companies_detected': 0, 'validation_passed': False}
                }

    def _extract_with_structured_prompt(self, image_path: str, retry_count: int) -> Dict:
        """Retry extraction with structured JSON prompt to ensure all 6 companies are captured"""
        logger.info(f"Using structured extraction for {Path(image_path).name}")

        try:
            with open(image_path, 'rb') as f:
                image_bytes = f.read()

            image_part = Part.from_data(image_bytes, mime_type="image/png")

            # More structured prompt that asks for JSON output
            prompt = """This is a page from a medical equipment catalog with EXACTLY 6 company entries.

The page has a 2x3 grid layout:
- Top Left | Top Right
- Middle Left | Middle Right
- Bottom Left | Bottom Right

Extract ALL 6 companies and return as a JSON array with this format:
[
  {
    "position": "top-left",
    "company_name_zh": "Chinese name",
    "company_name_en": "English name",
    "booth_number": "booth#",
    "address": "full address",
    "contact": {
      "email": "email@example.com",
      "phone": "phone",
      "website": "website"
    },
    "description": "product description"
  },
  ... (repeat for all 6 companies)
]

If a field is not visible, use null. But you MUST extract all 6 company entries."""

            response = self.model.generate_content([prompt, image_part])
            ocr_text = response.text

            company_count = self._count_companies_in_text(ocr_text)

            return {
                'image_path': image_path,
                'text': ocr_text,
                'confidence': 0.95,
                'metadata': {
                    'page': self._extract_page_number(image_path),
                    'timestamp': time.time(),
                    'model': self.model_name,
                    'char_count': len(ocr_text),
                    'companies_detected': company_count,
                    'validation_passed': company_count >= 6,
                    'structured_retry': True
                }
            }

        except Exception as e:
            logger.error(f"Structured extraction failed for {image_path}: {e}")
            # Fall back to regular result
            return self.extract_text_from_image(image_path, retry_count + 1)

    def _count_companies_in_text(self, text: str) -> int:
        """
        Count approximate number of companies in extracted text
        Uses booth number pattern as primary indicator
        """
        import re

        # Count booth numbers (most reliable indicator)
        # Format: X.XYZ## or X.XYZC##,X.XYZC## (for multiple booths)
        booth_pattern = r'\b\d+\.\d+[A-Z]+\d+'
        booth_matches = re.findall(booth_pattern, text)

        # Also count company name patterns
        # Look for "Co.,Ltd", "Company", "Corp", "Inc" etc
        company_suffixes = [
            r'Co\.,?\s*Ltd',
            r'Company',
            r'Corporation',
            r'Corp\.',
            r'Inc\.',
            r'Limited'
        ]

        company_name_count = 0
        for suffix in company_suffixes:
            company_name_count += len(re.findall(suffix, text, re.IGNORECASE))

        # Use the higher count (booth numbers are more reliable)
        estimated_count = max(len(booth_matches), company_name_count)

        return estimated_count

    def extract_text_from_batch(self, image_paths: List[str]) -> List[Dict]:
        """
        Extract text from a batch of images

        Args:
            image_paths: List of image file paths

        Returns:
            List of OCR results
        """
        logger.info(f"Processing batch of {len(image_paths)} images with Gemini")
        batch_start = time.time()

        results = []
        for i, image_path in enumerate(image_paths, 1):
            try:
                result = self.extract_text_from_image(image_path)
                results.append(result)

                # Rate limiting - Gemini has generous limits but be safe
                if i < len(image_paths):  # Don't sleep after last image
                    time.sleep(1)  # 1 second between requests

                if i % 5 == 0:
                    elapsed = time.time() - batch_start
                    avg_time = elapsed / i
                    eta = avg_time * (len(image_paths) - i)
                    logger.info(f"Progress: {i}/{len(image_paths)} ({i/len(image_paths)*100:.1f}%) - ETA: {eta/60:.1f}m")

            except Exception as e:
                logger.error(f"Failed to process {image_path}: {e}")
                results.append({
                    'image_path': image_path,
                    'text': '',
                    'confidence': 0.0,
                    'metadata': {'error': str(e)}
                })

        batch_time = time.time() - batch_start
        logger.info(f"Batch completed in {batch_time:.2f}s ({batch_time/len(image_paths):.2f}s per image)")

        return results

    def _extract_page_number(self, image_path: str) -> Optional[int]:
        """Extract page number from image filename"""
        try:
            filename = Path(image_path).stem
            # Assumes format like "page_0001.png"
            if 'page_' in filename:
                page_num = int(filename.split('_')[-1])
                return page_num
        except Exception:
            pass
        return None

    def cleanup(self):
        """Cleanup resources"""
        logger.info("Cleaning up Gemini OCR client")
        # No resources to clean up


__all__ = ['GeminiOCRClient']
