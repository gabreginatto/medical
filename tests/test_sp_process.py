#!/usr/bin/env python3
"""
Test SP State Processing - Limited to 5 Finalized Tenders
Tests the complete processing pipeline with a small sample
"""

import asyncio
import logging
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to path (parent of tests directory)
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import ProcessingConfig
from database import CloudSQLManager, DatabaseOperations
from pncp_api import PNCPAPIClient
from classifier import TenderClassifier
from optimized_discovery import OptimizedTenderDiscovery
from item_processor import ItemProcessor
from product_matcher import ProductMatcher
import csv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_sp_processing():
    """Test processing 5 finalized tenders from SP state"""

    print("=" * 70)
    print("SP STATE PROCESSING TEST - 5 FINALIZED TENDERS")
    print("=" * 70)

    # Configuration - only SP state, recent date range
    config = ProcessingConfig(
        enabled_states=['SP'],
        min_tender_value=1000.0,  # Lower threshold to get results
        max_tender_value=5_000_000.0,
        min_match_score=15.0,  # Lower threshold to catch medical-relevant tenders
        allowed_modalities=[6, 8]  # Pregão Eletrônico, Dispensa
    )

    # Date range - last 60 days to find completed tenders
    end_date = datetime.now()
    start_date = end_date - timedelta(days=60)
    start_date_str = start_date.strftime('%Y%m%d')
    end_date_str = end_date.strftime('%Y%m%d')

    print(f"\n📅 Date Range: {start_date_str} to {end_date_str} (60 days)")
    print(f"📍 State: São Paulo (SP)")
    print(f"🎯 Target: 5 finalized tenders with homologated prices")
    print(f"💰 Value Range: R${config.min_tender_value:,.2f} - R${config.max_tender_value:,.2f}")

    try:
        # Initialize database
        print("\n1️⃣  Initializing database connection...")

        # Get database config from environment
        project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
        region = os.getenv('CLOUD_SQL_REGION')
        instance_name = os.getenv('CLOUD_SQL_INSTANCE')
        database_name = os.getenv('DATABASE_NAME')

        if not all([project_id, region, instance_name]):
            raise ValueError("Missing required environment variables: GOOGLE_CLOUD_PROJECT, CLOUD_SQL_REGION, CLOUD_SQL_INSTANCE")

        print(f"   Project: {project_id}")
        print(f"   Instance: {region}:{instance_name}")
        print(f"   Database: {database_name}")

        db_manager = CloudSQLManager(project_id, region, instance_name, database_name)
        db_ops = DatabaseOperations(db_manager)
        print("   ✅ Database manager created")

        # Initialize components
        print("\n2️⃣  Initializing API client and classifier...")
        api_client = PNCPAPIClient()
        await api_client.start_session()
        classifier = TenderClassifier()

        # Load Fernandes catalog (if available)
        fernandes_products = []
        catalog_path = os.getenv('FERNANDES_CATALOG_CSV', '')
        if catalog_path and os.path.exists(catalog_path):
            with open(catalog_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                fernandes_products = list(reader)
            print(f"   📦 Loaded {len(fernandes_products)} Fernandes products")

        product_matcher = ProductMatcher()
        print("   ✅ Components initialized")

        # Create discovery engine (V2)
        discovery_engine = OptimizedTenderDiscovery(api_client, classifier, db_ops, config)

        # Discover tenders (limited sample)
        print("\n3️⃣  Discovering tenders in SP state (optimized V2 pipeline)...")
        print("   (Looking for finalized tenders with homologated prices)")

        medical_tenders, metrics = await discovery_engine.discover_medical_tenders_optimized(
            'SP', start_date_str, end_date_str
        )

        stats = type('Stats', (), {
            'total_found': metrics.stage1_bulk_fetch.tenders_out,
            'medical_relevant': len(medical_tenders),
            'processing_time_seconds': metrics.total_duration
        })()

        print(f"\n   📊 Discovery Results:")
        print(f"   - Total Found: {stats.total_found}")
        print(f"   - Medical Relevant: {stats.medical_relevant}")
        print(f"   - Processing Time: {stats.processing_time_seconds:.1f}s")

        if stats.medical_relevant == 0:
            print("\n   ⚠️  No medical-relevant tenders found in this date range")
            print("   Try increasing date range or lowering match threshold")
            return

        # Get tenders that need item processing (limit to 5)
        print("\n4️⃣  Getting finalized tenders for item extraction (limit: 5)...")
        unprocessed_tenders = await db_ops.get_unprocessed_tenders(state_code='SP', limit=5)

        print(f"   Found {len(unprocessed_tenders)} tenders ready for processing")

        if not unprocessed_tenders:
            print("\n   ℹ️  All tenders already processed or no tenders available")
            return

        # Display tender summary
        print("\n   📋 Tenders to Process:")
        for i, tender in enumerate(unprocessed_tenders, 1):
            print(f"\n   {i}. {tender.get('title', 'N/A')[:60]}...")
            print(f"      Control Number: {tender.get('control_number', 'N/A')}")
            print(f"      Organization: {tender.get('organization_name', 'N/A')[:50]}")
            print(f"      Homologated Value: R$ {tender.get('total_homologated_value', 0):,.2f}")
            print(f"      Government Level: {tender.get('government_level', 'N/A')}")

        # Process items
        print("\n5️⃣  Processing tender items...")
        usd_to_brl = float(os.getenv('USD_TO_BRL_RATE', '5.0'))
        item_processor = ItemProcessor(
            api_client, product_matcher, db_ops, fernandes_products, usd_to_brl
        )

        total_items = 0
        total_matches = 0

        for i, tender in enumerate(unprocessed_tenders, 1):
            print(f"\n   Processing tender {i}/{len(unprocessed_tenders)}...")
            print(f"   Control: {tender.get('control_number', 'N/A')}")

            try:
                result = await item_processor.process_tender_items(
                    tender['id'],
                    tender['cnpj'],
                    tender['ano'],
                    tender['sequencial']
                )

                print(f"   ✅ Items: {result.total_items_found}, Matches: {result.matched_products}")
                total_items += result.total_items_found
                total_matches += result.matched_products

                # Show sample items if any
                if result.total_items_found > 0:
                    print(f"   📦 Sample items from this tender:")
                    # Get items from database
                    items = await db_ops.get_tender_items(tender['id'], limit=3)
                    for item in items:
                        print(f"      - {item.get('description', 'N/A')[:60]}")
                        print(f"        Quantity: {item.get('quantity', 0)}, Unit Price: R$ {item.get('homologated_unit_value', 0):,.2f}")
                        if item.get('matched_product_id'):
                            print(f"        ✅ Matched to product")

            except Exception as e:
                print(f"   ❌ Error processing tender: {e}")
                logger.error(f"Error processing tender {tender.get('control_number')}: {e}")

        # Final summary
        print("\n" + "=" * 70)
        print("📊 PROCESSING SUMMARY")
        print("=" * 70)
        print(f"Tenders Discovered: {stats.medical_relevant}")
        print(f"Tenders Processed: {len(unprocessed_tenders)}")
        print(f"Total Items Extracted: {total_items}")
        print(f"Total Items Matched: {total_matches}")
        if total_items > 0:
            match_rate = (total_matches / total_items) * 100
            print(f"Match Rate: {match_rate:.1f}%")
        print(f"Processing Time: {stats.processing_time_seconds:.1f}s")

        if hasattr(stats, 'errors') and stats.errors:
            print(f"\n⚠️  Errors Encountered: {len(stats.errors)}")
            for error in stats.errors[:3]:
                print(f"   - {error}")

        print("\n✅ Test completed successfully!")
        print("\n💡 Next Steps:")
        print("   1. Review the matched items in the database")
        print("   2. Check match quality and scoring")
        print("   3. Adjust min_match_score if needed")
        print("   4. Scale up to process more tenders")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        logger.error(f"Test failed: {e}", exc_info=True)
        raise

    finally:
        # Cleanup
        if 'api_client' in locals():
            await api_client.close_session()
        if 'db_manager' in locals():
            await db_manager.close()
            print("\n🔒 Database connection closed")

if __name__ == "__main__":
    asyncio.run(test_sp_processing())