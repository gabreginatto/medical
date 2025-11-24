#!/usr/bin/env python3
"""
Step 1: OCR Extraction

Converts CMEF PDF catalog to text using DeepSeek OCR via Vertex AI.

Workflow:
1. Split PDF into page batches
2. Convert pages to images
3. Apply preprocessing (optional)
4. Run DeepSeek OCR on images
5. Save raw OCR output with metadata
"""

import json
import logging
import time
from datetime import datetime
from pathlib import Path

from config import CMEFConfig, DEFAULT_CONFIG
from utils.pdf_preprocessor import PDFPreprocessor, estimate_processing_time
from utils.gemini_ocr_client import GeminiOCRClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/ocr_extraction.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class OCRExtractor:
    """Extracts text from CMEF PDF using OCR"""

    def __init__(self, config: CMEFConfig = DEFAULT_CONFIG):
        """
        Initialize OCR extractor

        Args:
            config: CMEF configuration
        """
        self.config = config
        self.preprocessor = PDFPreprocessor(config)

        # Initialize Gemini OCR client
        logger.info("Using Gemini 2.5 Flash Lite OCR via Vertex AI")
        self.ocr_client = GeminiOCRClient(config)

        self.results = []

    def process_pdf(self, pdf_path: str = None, max_pages: int = None, start_page: int = None) -> dict:
        """
        Process PDF and extract text

        Args:
            pdf_path: Path to PDF file (uses config default if None)
            max_pages: Maximum number of pages to process (for testing)
            start_page: Page number to start from (1-indexed)

        Returns:
            Dictionary with OCR results
        """
        pdf_path = pdf_path or self.config.PDF_PATH

        logger.info("=" * 70)
        logger.info("STEP 1: OCR EXTRACTION - Gemini 2.5 Flash Lite")
        logger.info("=" * 70)
        logger.info(f"PDF: {pdf_path}")
        logger.info(f"OCR Engine: Gemini 2.5 Flash Lite (Vertex AI)")
        logger.info(f"Start page: {start_page or 1}")
        logger.info(f"Max pages: {max_pages or 'All'}")

        # Estimate processing time
        logger.info("\nEstimating processing time...")
        estimates = estimate_processing_time(pdf_path, self.config)
        if estimates:
            logger.info(f"  Total pages: {estimates['total_pages']}")
            logger.info(f"  Number of batches: {estimates['num_batches']}")
            logger.info(f"  Estimated time: {estimates['estimated_hours']:.1f} hours ({estimates['estimated_minutes']:.0f} minutes)")

        # Start processing
        start_time = time.time()

        # Extract pages in batches
        logger.info("\n" + "=" * 70)
        logger.info("PHASE 1: PDF to Images")
        logger.info("=" * 70)

        # Limit extraction if max_pages specified
        if max_pages or start_page:
            if max_pages:
                logger.info(f"Limiting extraction to {max_pages} pages")
            if start_page:
                logger.info(f"Starting from page {start_page}")
            batches = self.preprocessor.extract_pdf_pages_in_batches(pdf_path, max_pages=max_pages, start_page=start_page)
        else:
            batches = self.preprocessor.extract_pdf_pages_in_batches(pdf_path)

        # Process each batch
        logger.info("\n" + "=" * 70)
        logger.info("PHASE 2: OCR Processing")
        logger.info("=" * 70)

        all_ocr_results = []
        total_batches = len(batches)

        for batch_num, (first_page, last_page, image_paths) in enumerate(batches, 1):
            logger.info(f"\n{'='*70}")
            logger.info(f"Batch {batch_num}/{total_batches}: Pages {first_page}-{last_page}")
            logger.info(f"{'='*70}")

            batch_start = time.time()

            # Run OCR on batch
            ocr_results = self.ocr_client.extract_text_from_batch(image_paths)

            batch_time = time.time() - batch_start
            logger.info(f"Batch completed in {batch_time:.2f}s")

            # Calculate statistics
            total_chars = sum(len(r['text']) for r in ocr_results)
            avg_confidence = sum(r['confidence'] for r in ocr_results) / len(ocr_results) if ocr_results else 0

            logger.info(f"Extracted {total_chars:,} characters (avg confidence: {avg_confidence:.2f})")

            all_ocr_results.extend(ocr_results)

            # Progress update
            elapsed = time.time() - start_time
            avg_batch_time = elapsed / batch_num
            remaining_batches = total_batches - batch_num
            eta_seconds = avg_batch_time * remaining_batches
            eta_minutes = eta_seconds / 60

            logger.info(f"\nProgress: {batch_num}/{total_batches} batches ({batch_num/total_batches*100:.1f}%)")
            logger.info(f"ETA: {eta_minutes:.1f} minutes ({eta_seconds:.0f}s)")

        # Save results
        total_time = time.time() - start_time
        output_data = {
            'extracted_at': datetime.now().isoformat(),
            'pdf_path': pdf_path,
            'total_pages': sum(last - first + 1 for first, last, _ in batches),
            'total_batches': total_batches,
            'processing_time_seconds': total_time,
            'ocr_engine': 'Gemini 2.5 Flash Lite',
            'pages': all_ocr_results
        }

        # Save to file
        output_file = self.config.get_full_path(self.config.OCR_OUTPUT_FILE)
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        # Print summary
        logger.info("\n" + "=" * 70)
        logger.info("OCR EXTRACTION COMPLETE")
        logger.info("=" * 70)
        logger.info(f"Total pages processed: {output_data['total_pages']}")
        logger.info(f"Total processing time: {total_time/60:.1f} minutes ({total_time:.0f}s)")

        total_chars = sum(len(p['text']) for p in all_ocr_results)
        avg_confidence = sum(p['confidence'] for p in all_ocr_results) / len(all_ocr_results) if all_ocr_results else 0

        logger.info(f"Total characters extracted: {total_chars:,}")
        logger.info(f"Average confidence: {avg_confidence:.2f}")

        # Validation summary (6 companies per page)
        logger.info("\n" + "=" * 70)
        logger.info("VALIDATION SUMMARY (6 companies per page expected)")
        logger.info("=" * 70)

        total_companies = 0
        pages_with_6 = 0
        pages_with_issues = []

        for result in all_ocr_results:
            metadata = result.get('metadata', {})
            companies_detected = metadata.get('companies_detected', 0)
            total_companies += companies_detected

            if companies_detected >= 6:
                pages_with_6 += 1
            else:
                page_num = metadata.get('page', 'unknown')
                pages_with_issues.append((page_num, companies_detected))

        expected_companies = output_data['total_pages'] * 6
        logger.info(f"Total companies extracted: {total_companies}")
        logger.info(f"Expected companies (6 per page): {expected_companies}")
        logger.info(f"Coverage: {total_companies/expected_companies*100:.1f}%")
        logger.info(f"\nPages with all 6 companies: {pages_with_6}/{output_data['total_pages']}")

        if pages_with_issues:
            logger.warning(f"\n⚠️ Pages with incomplete extraction ({len(pages_with_issues)} pages):")
            for page_num, count in pages_with_issues[:20]:  # Show first 20
                logger.warning(f"  Page {page_num}: {count}/6 companies")
            if len(pages_with_issues) > 20:
                logger.warning(f"  ... and {len(pages_with_issues) - 20} more pages")

        logger.info(f"\nOutput saved to: {output_file}")
        logger.info(f"\nNext step: Run step2_parse_and_structure.py")

        return output_data

    def cleanup_temp_files(self):
        """Clean up temporary image files"""
        logger.info("\nCleaning up temporary files...")
        self.preprocessor.cleanup_images()


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Extract text from CMEF PDF using OCR")
    parser.add_argument(
        '--pdf',
        type=str,
        help='Path to PDF file (default: from config)'
    )
    parser.add_argument(
        '--max-pages',
        type=int,
        help='Maximum number of pages to process (for testing)'
    )
    parser.add_argument(
        '--start-page',
        type=int,
        help='Page number to start from (1-indexed)'
    )
    parser.add_argument(
        '--cleanup',
        action='store_true',
        help='Clean up temporary image files after processing'
    )

    args = parser.parse_args()

    # Initialize extractor
    extractor = OCRExtractor()

    try:
        # Process PDF
        results = extractor.process_pdf(
            pdf_path=args.pdf,
            max_pages=args.max_pages,
            start_page=args.start_page
        )

        # Cleanup if requested
        if args.cleanup:
            extractor.cleanup_temp_files()

        logger.info("\n✅ OCR extraction completed successfully!")

    except KeyboardInterrupt:
        logger.warning("\n⚠️  Process interrupted by user")
    except Exception as e:
        logger.error(f"\n❌ Error during OCR extraction: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise


if __name__ == "__main__":
    main()
