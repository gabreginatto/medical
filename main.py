"""
PNCP Medical Data Processing - Main Orchestration Module
Coordinates the complete workflow from tender discovery to price analysis
"""

import asyncio
import logging
import json
import os
import argparse
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import pandas as pd

from config import (
    ProcessingConfig, DatabaseConfig, get_state_codes,
    BRAZILIAN_STATES, DEFAULT_CONFIG
)
from database import CloudSQLManager, DatabaseOperations, create_db_manager_from_env
from pncp_api import PNCPAPIClient, test_api_connection
from classifier import TenderClassifier
from tender_discovery import TenderDiscoveryEngine, create_discovery_engine, print_discovery_stats
from item_processor import ItemProcessor, ProductCatalogManager, create_sample_fernandes_catalog
from product_matcher import ProductMatcher

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('pncp_processing.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class PNCPMedicalProcessor:
    """Main orchestration class for PNCP medical data processing"""

    def __init__(self, config: ProcessingConfig = None):
        self.config = config or DEFAULT_CONFIG
        self.db_manager: Optional[CloudSQLManager] = None
        self.db_ops: Optional[DatabaseOperations] = None
        self.api_client: Optional[PNCPAPIClient] = None
        self.classifier: Optional[TenderClassifier] = None
        self.product_matcher: Optional[ProductMatcher] = None
        self.discovery_engine: Optional[TenderDiscoveryEngine] = None
        self.item_processor: Optional[ItemProcessor] = None
        self.catalog_manager: Optional[ProductCatalogManager] = None
        self.fernandes_products: List[Dict] = []

    async def initialize(self):
        """Initialize all components"""
        logger.info("Initializing PNCP Medical Processor...")

        try:
            # Initialize database
            await self._initialize_database()

            # Initialize API client
            await self._initialize_api_client()

            # Initialize product catalog
            self._initialize_product_catalog()

            # Initialize processing components
            self._initialize_processors()

            logger.info("Initialization completed successfully")

        except Exception as e:
            logger.error(f"Initialization failed: {e}")
            raise

    async def _initialize_database(self):
        """Initialize Cloud SQL database connection"""
        logger.info("Initializing database connection...")

        try:
            self.db_manager = create_db_manager_from_env()
            self.db_ops = DatabaseOperations(self.db_manager)

            # Initialize database schema
            await self.db_ops.initialize_database()

            logger.info("Database initialized successfully")

        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise

    async def _initialize_api_client(self):
        """Initialize PNCP API client and test connection"""
        logger.info("Initializing API client...")

        username = os.getenv('PNCP_USERNAME')
        password = os.getenv('PNCP_PASSWORD')

        if not username or not password:
            raise ValueError("PNCP_USERNAME and PNCP_PASSWORD environment variables required")

        self.api_client = PNCPAPIClient(username, password)

        # Test connection
        success = await test_api_connection(username, password)
        if not success:
            raise RuntimeError("Failed to connect to PNCP API")

        logger.info("API client initialized and tested successfully")

    def _initialize_product_catalog(self):
        """Initialize Fernandes product catalog"""
        logger.info("Initializing product catalog...")

        self.catalog_manager = ProductCatalogManager()

        # Try to load from CSV if available
        catalog_csv = os.getenv('FERNANDES_CATALOG_CSV')
        if catalog_csv and os.path.exists(catalog_csv):
            self.catalog_manager.load_catalog_from_csv(catalog_csv)
        else:
            # Use sample catalog for testing
            logger.warning("Using sample catalog - set FERNANDES_CATALOG_CSV environment variable for production")
            sample_products = create_sample_fernandes_catalog()
            self.catalog_manager.load_catalog_from_pdf_data(sample_products)

        self.fernandes_products = self.catalog_manager.get_products()
        logger.info(f"Product catalog initialized with {len(self.fernandes_products)} products")

    def _initialize_processors(self):
        """Initialize processing components"""
        logger.info("Initializing processing components...")

        self.classifier = TenderClassifier()
        self.product_matcher = ProductMatcher()

        self.discovery_engine = TenderDiscoveryEngine(
            self.api_client, self.classifier, self.db_ops, self.config
        )

        self.item_processor = ItemProcessor(
            self.api_client, self.product_matcher, self.db_ops, self.fernandes_products
        )

        logger.info("Processing components initialized")

    async def discover_tenders(self, start_date: str, end_date: str,
                             states: List[str] = None, chunk_days: int = 7):
        """Discover tenders for specified date range and states"""

        if not self.discovery_engine:
            raise RuntimeError("Discovery engine not initialized")

        states = states or self.config.enabled_states
        logger.info(f"Starting tender discovery for {len(states)} states: {start_date} to {end_date}")

        if chunk_days > 0:
            # Process in chunks to avoid API limits
            chunk_results = await self.discovery_engine.discover_by_date_chunks(
                start_date, end_date, chunk_days, states
            )

            # Combine statistics
            total_stats = chunk_results[0] if chunk_results else None
            for chunk_stats in chunk_results[1:]:
                if total_stats:
                    total_stats.total_found += chunk_stats.total_found
                    total_stats.medical_relevant += chunk_stats.medical_relevant
                    total_stats.processing_time_seconds += chunk_stats.processing_time_seconds
                    total_stats.errors.extend(chunk_stats.errors)

                    # Merge dictionaries
                    for key, value in chunk_stats.by_state.items():
                        total_stats.by_state[key] = total_stats.by_state.get(key, 0) + value

            return total_stats
        else:
            # Process all at once
            return await self.discovery_engine.discover_tenders_for_date_range(
                start_date, end_date, states
            )

    async def process_tender_items(self, state_code: str = None, limit: int = 50):
        """Process items for unprocessed tenders"""

        if not self.item_processor:
            raise RuntimeError("Item processor not initialized")

        logger.info(f"Processing tender items for state: {state_code or 'all'}, limit: {limit}")

        # Get unprocessed tenders
        unprocessed_tenders = await self.db_ops.get_unprocessed_tenders(state_code, limit)

        if not unprocessed_tenders:
            logger.info("No unprocessed tenders found")
            return []

        logger.info(f"Found {len(unprocessed_tenders)} unprocessed tenders")

        # Process tenders
        results = await self.item_processor.process_multiple_tenders(unprocessed_tenders)

        return results

    async def run_complete_workflow(self, start_date: str, end_date: str,
                                  states: List[str] = None, chunk_days: int = 7):
        """Run complete workflow: discovery -> item processing -> analysis"""

        logger.info("Starting complete PNCP medical data workflow")

        workflow_start = datetime.now()

        try:
            # Phase 1: Tender Discovery
            logger.info("=== Phase 1: Tender Discovery ===")
            discovery_stats = await self.discover_tenders(start_date, end_date, states, chunk_days)

            if discovery_stats:
                print_discovery_stats(discovery_stats)

                if discovery_stats.medical_relevant == 0:
                    logger.warning("No medical relevant tenders found")
                    return

            # Phase 2: Item Processing
            logger.info("=== Phase 2: Item Processing ===")
            item_results = []

            # Process each state separately to manage memory
            states_to_process = states or self.config.enabled_states
            for state in states_to_process:
                logger.info(f"Processing items for {state}...")
                state_results = await self.process_tender_items(state, limit=20)
                item_results.extend(state_results)

                # Small delay between states
                await asyncio.sleep(1)

            # Phase 3: Generate Reports
            logger.info("=== Phase 3: Generating Reports ===")
            await self.generate_reports(discovery_stats, item_results)

            total_time = (datetime.now() - workflow_start).total_seconds()
            logger.info(f"Complete workflow finished in {total_time:.1f} seconds")

        except Exception as e:
            logger.error(f"Workflow failed: {e}")
            raise

    async def generate_reports(self, discovery_stats, item_results):
        """Generate analysis reports"""

        logger.info("Generating analysis reports...")

        reports = {
            'discovery_summary': {
                'total_tenders_found': discovery_stats.total_found if discovery_stats else 0,
                'medical_relevant': discovery_stats.medical_relevant if discovery_stats else 0,
                'by_state': discovery_stats.by_state if discovery_stats else {},
                'by_government_level': discovery_stats.by_government_level if discovery_stats else {},
                'processing_time': discovery_stats.processing_time_seconds if discovery_stats else 0
            },
            'item_processing_summary': {
                'tenders_processed': len(item_results),
                'total_items': sum(r.total_items_found for r in item_results),
                'items_with_homologated_prices': sum(r.items_with_results for r in item_results),
                'total_matches': sum(r.matched_products for r in item_results),
                'total_value_brl': sum(r.total_homologated_value for r in item_results)
            },
            'timestamp': datetime.now().isoformat()
        }

        # Save report to file
        report_filename = f"pncp_medical_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_filename, 'w') as f:
            json.dump(reports, f, indent=2, default=str)

        logger.info(f"Report saved to {report_filename}")

        # Print summary
        print("\n=== WORKFLOW SUMMARY ===")
        print(f"Tenders Found: {reports['discovery_summary']['total_tenders_found']:,}")
        print(f"Medical Relevant: {reports['discovery_summary']['medical_relevant']:,}")
        print(f"Items Processed: {reports['item_processing_summary']['total_items']:,}")
        print(f"Product Matches: {reports['item_processing_summary']['total_matches']:,}")
        print(f"Total Value: R${reports['item_processing_summary']['total_value_brl']:,.2f}")

    async def export_data_to_csv(self, output_dir: str = "exports"):
        """Export processed data to CSV files"""

        logger.info("Exporting data to CSV...")

        # Create output directory
        os.makedirs(output_dir, exist_ok=True)

        # This would need to be implemented based on database schema
        # For now, just create placeholder files
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # Export tenders
        tenders_file = f"{output_dir}/tenders_{timestamp}.csv"
        logger.info(f"Would export tenders to {tenders_file}")

        # Export matched products
        matches_file = f"{output_dir}/matched_products_{timestamp}.csv"
        logger.info(f"Would export matches to {matches_file}")

    async def cleanup(self):
        """Clean up resources"""
        logger.info("Cleaning up resources...")

        if self.api_client:
            await self.api_client.close_session()

        if self.db_manager:
            await self.db_manager.close()

        logger.info("Cleanup completed")

async def main():
    """Main entry point"""

    parser = argparse.ArgumentParser(description='PNCP Medical Data Processor')
    parser.add_argument('--start-date', required=True, help='Start date (YYYYMMDD)')
    parser.add_argument('--end-date', required=True, help='End date (YYYYMMDD)')
    parser.add_argument('--states', nargs='*', help='State codes to process (default: all)')
    parser.add_argument('--chunk-days', type=int, default=7, help='Days per processing chunk')
    parser.add_argument('--discovery-only', action='store_true', help='Only run discovery phase')
    parser.add_argument('--items-only', action='store_true', help='Only process items (skip discovery)')
    parser.add_argument('--config-file', help='Configuration file path')

    args = parser.parse_args()

    # Load configuration
    config = DEFAULT_CONFIG
    if args.config_file and os.path.exists(args.config_file):
        with open(args.config_file, 'r') as f:
            config_data = json.load(f)
            # Would need to implement config loading
            logger.info(f"Loaded configuration from {args.config_file}")

    # Validate states
    if args.states:
        invalid_states = [s for s in args.states if s not in get_state_codes()]
        if invalid_states:
            logger.error(f"Invalid state codes: {invalid_states}")
            return

    processor = PNCPMedicalProcessor(config)

    try:
        await processor.initialize()

        if args.discovery_only:
            logger.info("Running discovery only...")
            stats = await processor.discover_tenders(
                args.start_date, args.end_date, args.states, args.chunk_days
            )
            if stats:
                print_discovery_stats(stats)

        elif args.items_only:
            logger.info("Processing items only...")
            results = await processor.process_tender_items(limit=100)
            logger.info(f"Processed items for {len(results)} tenders")

        else:
            logger.info("Running complete workflow...")
            await processor.run_complete_workflow(
                args.start_date, args.end_date, args.states, args.chunk_days
            )

    except KeyboardInterrupt:
        logger.info("Process interrupted by user")

    except Exception as e:
        logger.error(f"Process failed: {e}")
        raise

    finally:
        await processor.cleanup()

# Quick test functions
async def test_setup():
    """Test basic setup and configuration"""

    print("=== PNCP Medical Processor Test ===")

    # Test configuration
    print(f"Default config states: {len(DEFAULT_CONFIG.enabled_states)}")
    print(f"Modalities: {DEFAULT_CONFIG.allowed_modalities}")

    # Test product matching
    matcher = ProductMatcher()
    sample_products = create_sample_fernandes_catalog()

    test_item = "CURATIVO TRANSPARENTE 6X7CM COM BORDA ADESIVA"
    result = matcher.find_best_match(test_item, sample_products)

    if result:
        product, score = result
        print(f"Match test: '{test_item}' -> {product['CÓDIGO']} ({score:.1f}%)")
    else:
        print(f"Match test: No match found for '{test_item}'")

    print("Test completed")

async def run_demo():
    """Run a demonstration with recent data"""

    print("=== PNCP Demo Mode ===")

    # Use recent dates
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)

    start_date_str = start_date.strftime('%Y%m%d')
    end_date_str = end_date.strftime('%Y%m%d')

    # Test with just DF (Federal District)
    demo_states = ['DF']

    config = ProcessingConfig(
        enabled_states=demo_states,
        min_tender_value=5000.0,
        min_match_score=30.0
    )

    processor = PNCPMedicalProcessor(config)

    try:
        # Note: This would need proper credentials and database setup
        print(f"Demo would process {len(demo_states)} states from {start_date_str} to {end_date_str}")
        print("Requires proper PNCP credentials and Cloud SQL setup")

    except Exception as e:
        print(f"Demo setup failed (expected): {e}")

if __name__ == "__main__":
    # Check if running in demo mode
    if len(os.sys.argv) == 1 or '--demo' in os.sys.argv:
        asyncio.run(run_demo())
    elif '--test' in os.sys.argv:
        asyncio.run(test_setup())
    else:
        asyncio.run(main())