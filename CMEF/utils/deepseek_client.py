"""
DeepSeek OCR Client

Handles communication with DeepSeek OCR API Service via Vertex AI.
Uses the OpenAPI-compatible chat completions endpoint.
"""

import logging
import time
import base64
import json
import subprocess
from typing import List, Dict, Optional
from pathlib import Path

try:
    import requests
except ImportError:
    raise ImportError(
        "Missing required library: requests. "
        "Install with: pip install requests"
    )

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import CMEFConfig, DEFAULT_CONFIG

logger = logging.getLogger(__name__)


class DeepSeekOCRClient:
    """Client for DeepSeek OCR API Service via Vertex AI"""

    def __init__(self, config: CMEFConfig = DEFAULT_CONFIG):
        """
        Initialize DeepSeek OCR API client

        Args:
            config: CMEF configuration object
        """
        self.config = config
        self.api_endpoint = f"https://aiplatform.googleapis.com/v1/projects/{config.DEEPSEEK_PROJECT_ID}/locations/global/endpoints/openapi/chat/completions"
        self.model_name = "deepseek-ai/deepseek-ocr-maas"
        self._test_auth()

    def _test_auth(self):
        """Test that gcloud authentication is working"""
        try:
            result = subprocess.run(
                ["gcloud", "auth", "print-access-token"],
                capture_output=True,
                text=True,
                check=True
            )
            logger.info("✅ gcloud authentication verified")
        except subprocess.CalledProcessError as e:
            logger.error("❌ gcloud authentication failed")
            logger.error("Please run: gcloud auth login")
            raise RuntimeError("gcloud authentication required")
        except FileNotFoundError:
            logger.error("❌ gcloud CLI not found")
            raise RuntimeError("gcloud CLI not installed")

    def _get_access_token(self) -> str:
        """Get gcloud access token for API authentication"""
        try:
            result = subprocess.run(
                ["gcloud", "auth", "print-access-token"],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except Exception as e:
            logger.error(f"Failed to get access token: {e}")
            raise

    def _encode_image_to_data_url(self, image_path: str) -> str:
        """
        Encode image to base64 data URL

        Args:
            image_path: Path to image file

        Returns:
            Base64 data URL string (data:image/png;base64,...)
        """
        try:
            with open(image_path, 'rb') as f:
                image_bytes = f.read()

            # Detect image format
            ext = Path(image_path).suffix.lower()
            mime_type = {
                '.png': 'image/png',
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.gif': 'image/gif',
                '.webp': 'image/webp'
            }.get(ext, 'image/png')

            encoded = base64.b64encode(image_bytes).decode('utf-8')
            return f"data:{mime_type};base64,{encoded}"

        except Exception as e:
            logger.error(f"Failed to encode image {image_path}: {e}")
            raise

    def extract_text_from_image(self, image_path: str, retry_count: int = 0) -> Dict:
        """
        Extract text from a single image using DeepSeek OCR API Service

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
            # Get access token
            access_token = self._get_access_token()

            # Encode image to data URL
            image_data_url = self._encode_image_to_data_url(image_path)

            # Prepare API request payload
            # DeepSeek OCR API expects image_url to be an object with 'url' key
            # Also includes optimal OCR prompt
            payload = {
                "model": self.model_name,
                "stream": False,  # Get complete response at once
                "messages": [{
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": image_data_url  # ← Fixed: nested url key
                            }
                        },
                        {
                            "type": "text",
                            "text": "Free OCR."  # ← Added: recommended prompt
                        }
                    ]
                }]
            }

            # Make API call using requests library (avoids curl argument size limits)
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }

            response = requests.post(
                self.api_endpoint,
                headers=headers,
                json=payload,
                timeout=self.config.OCR_TIMEOUT
            )

            # Check for HTTP errors
            if response.status_code != 200:
                raise RuntimeError(f"API call failed with status {response.status_code}: {response.text}")

            # Parse response
            response_data = response.json()

            # Extract text from OpenAPI chat completion format
            if 'choices' in response_data and len(response_data['choices']) > 0:
                choice = response_data['choices'][0]
                message = choice.get('message', {})
                text = message.get('content', '').strip()

                ocr_result = {
                    'image_path': image_path,
                    'text': text,
                    'confidence': 0.95,  # API doesn't provide confidence, assume high quality
                    'metadata': {
                        'page': self._extract_page_number(image_path),
                        'timestamp': time.time(),
                        'model': self.model_name,
                        'finish_reason': choice.get('finish_reason')
                    }
                }

                logger.debug(f"Extracted {len(text)} characters")
                return ocr_result

            else:
                logger.warning(f"Unexpected API response format: {response_data}")
                return {
                    'image_path': image_path,
                    'text': '',
                    'confidence': 0.0,
                    'metadata': {'error': 'unexpected_response_format', 'response': str(response_data)}
                }

        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")

            if retry_count < self.config.OCR_MAX_RETRIES:
                logger.info(f"Retrying... (attempt {retry_count + 1}/{self.config.OCR_MAX_RETRIES})")
                time.sleep(self.config.OCR_RETRY_DELAY)
                return self.extract_text_from_image(image_path, retry_count + 1)
            else:
                return {
                    'image_path': image_path,
                    'text': '',
                    'confidence': 0.0,
                    'metadata': {'error': f'request_error: {str(e)}'}
                }

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse API response: {e}")

            if retry_count < self.config.OCR_MAX_RETRIES:
                logger.info(f"Retrying... (attempt {retry_count + 1}/{self.config.OCR_MAX_RETRIES})")
                time.sleep(self.config.OCR_RETRY_DELAY)
                return self.extract_text_from_image(image_path, retry_count + 1)
            else:
                return {
                    'image_path': image_path,
                    'text': '',
                    'confidence': 0.0,
                    'metadata': {'error': f'json_parse_error: {str(e)}'}
                }

        except Exception as e:
            logger.error(f"OCR failed for {image_path}: {e}")

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
        logger.info(f"Processing batch of {len(image_paths)} images")
        batch_start = time.time()

        results = []
        for i, image_path in enumerate(image_paths, 1):
            try:
                result = self.extract_text_from_image(image_path)
                results.append(result)

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
        """Cleanup resources (no-op for API Service)"""
        logger.info("Cleaning up DeepSeek OCR client")
        # No resources to clean up with API Service


# ==================== ALTERNATIVE: LOCAL OCR FALLBACK ====================

class LocalOCRClient:
    """
    Fallback OCR client using Tesseract (local)

    Use this if DeepSeek OCR is not available or too expensive.
    Note: Quality will be lower, especially for Chinese text.
    """

    def __init__(self):
        """Initialize local OCR client"""
        try:
            import pytesseract
            self.tesseract = pytesseract
            logger.info("Initialized local OCR client (Tesseract)")
        except ImportError:
            raise ImportError(
                "pytesseract not installed. "
                "Install with: pip install pytesseract"
            )

    def extract_text_from_image(self, image_path: str) -> Dict:
        """Extract text using Tesseract OCR"""
        try:
            from PIL import Image
            image = Image.open(image_path)

            # Extract text with Chinese + English support
            text = self.tesseract.image_to_string(
                image,
                lang='chi_sim+eng'  # Requires Chinese language data
            )

            return {
                'image_path': image_path,
                'text': text,
                'confidence': 0.8,  # Rough estimate
                'metadata': {
                    'engine': 'tesseract',
                    'timestamp': time.time()
                }
            }

        except Exception as e:
            logger.error(f"Tesseract OCR failed for {image_path}: {e}")
            return {
                'image_path': image_path,
                'text': '',
                'confidence': 0.0,
                'metadata': {'error': str(e)}
            }

    def extract_text_from_batch(self, image_paths: List[str]) -> List[Dict]:
        """Extract text from batch using Tesseract"""
        return [self.extract_text_from_image(path) for path in image_paths]


__all__ = ['DeepSeekOCRClient', 'LocalOCRClient']
