"""
PDF Preprocessor

Handles PDF to image conversion and image preprocessing for optimal OCR results.
"""

import logging
from typing import List, Tuple, Optional
from pathlib import Path
import numpy as np

try:
    from pdf2image import convert_from_path
    from PIL import Image, ImageEnhance, ImageFilter
    import cv2
except ImportError as e:
    raise ImportError(
        f"Missing required library: {e.name}. "
        "Install with: pip install pdf2image pillow opencv-python"
    )

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import CMEFConfig, DEFAULT_CONFIG

logger = logging.getLogger(__name__)


class PDFPreprocessor:
    """Converts PDF pages to preprocessed images for OCR"""

    def __init__(self, config: CMEFConfig = DEFAULT_CONFIG):
        """
        Initialize PDF preprocessor

        Args:
            config: CMEF configuration object
        """
        self.config = config
        logger.info(f"Initialized PDFPreprocessor with DPI={config.IMAGE_DPI}")

    def pdf_to_images(
        self,
        pdf_path: str,
        first_page: Optional[int] = None,
        last_page: Optional[int] = None,
        output_dir: Optional[str] = None
    ) -> List[str]:
        """
        Convert PDF pages to images

        Args:
            pdf_path: Path to PDF file
            first_page: First page to convert (1-indexed)
            last_page: Last page to convert (1-indexed)
            output_dir: Directory to save images (if None, uses temp directory)

        Returns:
            List of image file paths
        """
        logger.info(f"Converting PDF to images: {pdf_path}")
        logger.info(f"Page range: {first_page or 'start'} to {last_page or 'end'}")

        try:
            # Convert PDF to PIL Images
            images = convert_from_path(
                pdf_path,
                dpi=self.config.IMAGE_DPI,
                first_page=first_page,
                last_page=last_page,
                fmt='png'
            )

            logger.info(f"Converted {len(images)} pages to images")

            # Save images
            output_path = Path(output_dir or self.config.get_full_path(self.config.PDF_IMAGES_DIR))
            output_path.mkdir(parents=True, exist_ok=True)

            image_paths = []
            for i, image in enumerate(images, start=first_page or 1):
                image_file = output_path / f"page_{i:04d}.png"
                image.save(image_file, 'PNG')
                image_paths.append(str(image_file))

            logger.info(f"Saved {len(image_paths)} images to {output_path}")
            return image_paths

        except Exception as e:
            logger.error(f"Failed to convert PDF to images: {e}")
            raise

    def preprocess_image(self, image_path: str, output_path: Optional[str] = None) -> str:
        """
        Apply preprocessing to improve OCR accuracy

        Steps:
        1. Resize if image is too large
        2. Convert to grayscale
        3. Denoise
        4. Enhance contrast
        5. Sharpen

        Args:
            image_path: Path to input image
            output_path: Path to save preprocessed image (optional)

        Returns:
            Path to preprocessed image
        """
        logger.debug(f"Preprocessing image: {image_path}")

        try:
            # Load image
            pil_image = Image.open(image_path)

            # Step 1: Resize if too large
            if pil_image.size[0] > self.config.MAX_IMAGE_SIZE[0] or \
               pil_image.size[1] > self.config.MAX_IMAGE_SIZE[1]:
                logger.debug(f"Resizing image from {pil_image.size}")
                pil_image.thumbnail(self.config.MAX_IMAGE_SIZE, Image.Resampling.LANCZOS)

            # Step 2: Convert to grayscale
            if pil_image.mode != 'L':
                pil_image = pil_image.convert('L')

            # Convert to numpy array for OpenCV processing
            img_array = np.array(pil_image)

            # Step 3: Denoise (if enabled)
            if self.config.DENOISE:
                img_array = cv2.fastNlMeansDenoising(img_array, h=10)

            # Step 4: Enhance contrast (if enabled)
            if self.config.ENHANCE_CONTRAST:
                # Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)
                clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
                img_array = clahe.apply(img_array)

            # Convert back to PIL for final enhancements
            processed_image = Image.fromarray(img_array)

            # Step 5: Sharpen (if enabled)
            if self.config.SHARPEN:
                processed_image = processed_image.filter(ImageFilter.SHARPEN)

            # Save processed image
            if output_path is None:
                preprocessed_dir = Path(self.config.get_full_path(self.config.PREPROCESSED_IMAGES_DIR))
                preprocessed_dir.mkdir(parents=True, exist_ok=True)
                filename = Path(image_path).name
                output_path = str(preprocessed_dir / filename)

            processed_image.save(output_path, 'PNG')
            logger.debug(f"Saved preprocessed image: {output_path}")

            return output_path

        except Exception as e:
            logger.error(f"Failed to preprocess image {image_path}: {e}")
            # Return original image path on failure
            return image_path

    def preprocess_batch(self, image_paths: List[str]) -> List[str]:
        """
        Preprocess a batch of images

        Args:
            image_paths: List of image file paths

        Returns:
            List of preprocessed image paths
        """
        logger.info(f"Preprocessing batch of {len(image_paths)} images")

        preprocessed_paths = []
        for i, image_path in enumerate(image_paths, 1):
            try:
                preprocessed_path = self.preprocess_image(image_path)
                preprocessed_paths.append(preprocessed_path)

                if i % 10 == 0:
                    logger.info(f"Preprocessed {i}/{len(image_paths)} images")

            except Exception as e:
                logger.warning(f"Skipping image {image_path}: {e}")
                preprocessed_paths.append(image_path)  # Use original on failure

        logger.info(f"Completed preprocessing {len(preprocessed_paths)} images")
        return preprocessed_paths

    def extract_pdf_pages_in_batches(
        self,
        pdf_path: str,
        batch_size: Optional[int] = None,
        max_pages: Optional[int] = None,
        start_page: Optional[int] = None
    ) -> List[Tuple[int, int, List[str]]]:
        """
        Extract PDF pages in batches for memory-efficient processing

        Args:
            pdf_path: Path to PDF file
            batch_size: Number of pages per batch (uses config default if None)
            max_pages: Maximum number of pages to process (for testing)
            start_page: Page number to start from (1-indexed)

        Returns:
            List of tuples: (first_page, last_page, image_paths)
        """
        batch_size = batch_size or self.config.PAGES_PER_BATCH
        start_page = start_page or 1

        # Get total page count
        try:
            from PyPDF2 import PdfReader
            reader = PdfReader(pdf_path)
            total_pages_in_pdf = len(reader.pages)

            # Calculate end page
            if max_pages:
                end_page_limit = min(start_page + max_pages - 1, total_pages_in_pdf)
                logger.info(f"PDF has {total_pages_in_pdf} pages, processing from page {start_page} to {end_page_limit} ({max_pages} pages)")
            else:
                end_page_limit = total_pages_in_pdf
                logger.info(f"PDF has {total_pages_in_pdf} pages, processing from page {start_page} to end in batches of {batch_size}")

        except Exception as e:
            logger.error(f"Failed to read PDF: {e}")
            raise

        batches = []
        current_page = start_page
        while current_page <= end_page_limit:
            batch_end = min(current_page + batch_size - 1, end_page_limit)

            logger.info(f"Processing batch: pages {current_page}-{batch_end}")

            # Convert batch to images
            image_paths = self.pdf_to_images(pdf_path, current_page, batch_end)

            # Preprocess if enabled
            if self.config.APPLY_PREPROCESSING:
                image_paths = self.preprocess_batch(image_paths)

            batches.append((current_page, batch_end, image_paths))

            current_page = batch_end + 1

        logger.info(f"Created {len(batches)} batches from PDF")
        return batches

    def cleanup_images(self, directory: Optional[str] = None):
        """
        Clean up temporary image files

        Args:
            directory: Directory to clean (if None, cleans both image directories)
        """
        import shutil

        if directory:
            dirs_to_clean = [directory]
        else:
            dirs_to_clean = [
                self.config.get_full_path(self.config.PDF_IMAGES_DIR),
                self.config.get_full_path(self.config.PREPROCESSED_IMAGES_DIR)
            ]

        for dir_path in dirs_to_clean:
            try:
                if Path(dir_path).exists():
                    shutil.rmtree(dir_path)
                    logger.info(f"Cleaned up directory: {dir_path}")
            except Exception as e:
                logger.warning(f"Failed to clean up {dir_path}: {e}")


# ==================== UTILITY FUNCTIONS ====================

def estimate_processing_time(pdf_path: str, config: CMEFConfig = DEFAULT_CONFIG) -> dict:
    """
    Estimate processing time for a PDF

    Args:
        pdf_path: Path to PDF file
        config: CMEF configuration

    Returns:
        Dictionary with time estimates
    """
    try:
        from PyPDF2 import PdfReader
        reader = PdfReader(pdf_path)
        total_pages = len(reader.pages)

        # Rough estimates (in seconds per page)
        time_per_page = {
            'pdf_to_image': 0.5,
            'preprocessing': 0.3,
            'ocr': 3.0  # DeepSeek OCR
        }

        num_batches = (total_pages + config.PAGES_PER_BATCH - 1) // config.PAGES_PER_BATCH

        total_time = (
            time_per_page['pdf_to_image'] * total_pages +
            time_per_page['preprocessing'] * total_pages +
            time_per_page['ocr'] * total_pages
        )

        return {
            'total_pages': total_pages,
            'num_batches': num_batches,
            'pages_per_batch': config.PAGES_PER_BATCH,
            'estimated_minutes': total_time / 60,
            'estimated_hours': total_time / 3600
        }

    except Exception as e:
        logger.error(f"Failed to estimate processing time: {e}")
        return {}


__all__ = ['PDFPreprocessor', 'estimate_processing_time']
