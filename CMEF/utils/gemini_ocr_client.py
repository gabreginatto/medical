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

            # OCR prompt - optimized for catalog pages
            prompt = """Extract all text from this page from a Chinese medical equipment trade show catalog.

Please output the text accurately, preserving the layout structure. Include:
- Company names (Chinese and English)
- Booth numbers
- Addresses
- Contact information (email, phone, website)
- Product descriptions

Be precise and maintain formatting."""

            # Generate content
            response = self.model.generate_content([prompt, image_part])

            ocr_text = response.text

            ocr_result = {
                'image_path': image_path,
                'text': ocr_text,
                'confidence': 0.95,  # Gemini doesn't provide confidence, assume high quality
                'metadata': {
                    'page': self._extract_page_number(image_path),
                    'timestamp': time.time(),
                    'model': self.model_name,
                    'char_count': len(ocr_text)
                }
            }

            logger.debug(f"Extracted {len(ocr_text)} characters")
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
                    'metadata': {'error': str(e)}
                }

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
