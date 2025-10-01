#!/usr/bin/env python3
"""
Quick SP State Test - Get 5 Medical Tenders FAST
Optimized for speed: short date range, early exit, targeted search
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
from database import create_db_manager_from_env, DatabaseOperations
from pncp_api import PNCPAPIClient
from classifier import TenderClassifier
from optimized_discovery import OptimizedTenderDiscovery, print_metrics_summary
from item_processor import ItemProcessor
from product_matcher import ProductMatcher
import csv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def quick_test():
    """Quick test to get 5 medical tenders from SP"""

    print("=" * 70)
    print("⚡ QUICK SP TEST - Get 5 Medical Tenders FAST")
    print("=" * 70)

    # OPTIMIZED Configuration for speed
    config = ProcessingConfig(
        enabled_states=['SP'],
        min_tender_value=5_000.0,  # Lower threshold for more results
        max_tender_value=2_000_000.0,
        min_match_score=40.0,  # Lower threshold = more matches
        allowed_modalities=[6, 8],  # Pregão + Dispensa for more variety
        use_org_cache=True,  # Use cache to identify medical orgs faster
        catmat_boost_enabled=True  # Prioritize CATMAT-coded items
    )

    # Use August-September 2024 when PNCP had completed tenders
    # Going back further to find completed tenders with items
    end_date = datetime(2024, 9, 15)
    start_date = datetime(2024, 8, 15)  # 31 days prior

    # Format dates correctly for PNCP API (YYYYMMDD)
    start_date_str = start_date.strftime('%Y%m%d')
    end_date_str = end_date.strftime('%Y%m%d')

    print(f"\n🔍 Using August-September 2024 data (completed tenders)")
    print(f"   Start: {start_date_str} ({start_date.strftime('%Y-%m-%d')})")
    print(f"   End: {end_date_str} ({end_date.strftime('%Y-%m-%d')})")

    print(f"\n📅 Date Range: {start_date_str} to {end_date_str} (31 days)")
    print(f"📍 State: São Paulo (SP)")
    print(f"🎯 Target: Get at least 5 completed medical tenders quickly")
    print(f"⚡ Optimizations: Short date range, high score threshold, cache enabled")

    api_client = None
    db_manager = None

    try:
        # Initialize components
        print("\n1️⃣  Initializing components...")

        db_manager = create_db_manager_from_env()
        db_ops = DatabaseOperations(db_manager)

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
        print("   ✅ Components ready")

        # Create discovery engine
        discovery_engine = OptimizedTenderDiscovery(api_client, classifier, db_ops, config)

        # Run optimized discovery
        print("\n2️⃣  Discovering medical tenders (V2 4-stage pipeline)...")
        start_time = datetime.now()

        medical_tenders, metrics = await discovery_engine.discover_medical_tenders_optimized(
            'SP', start_date_str, end_date_str
        )

        elapsed = (datetime.now() - start_time).total_seconds()

        print(f"\n   ✅ Discovery complete in {elapsed:.1f}s")
        print(f"   📊 Found {len(medical_tenders)} medical tenders")

        # Print metrics
        print_metrics_summary(metrics)

        if len(medical_tenders) == 0:
            print("\n   ⚠️  No medical tenders found. Try:")
            print("      - Increasing date range (change days=14 to days=30)")
            print("      - Lowering min_match_score (try 40.0)")
            print("      - Adding more modalities (add [8] for Dispensa)")
            return

        # Check for completed tenders with items
        print(f"\n3️⃣  Finding completed tenders with items...")

        completed_tenders = []
        for tender in medical_tenders[:20]:  # Check first 20 to find 5 completed
            if tender.get('valorTotalHomologado', 0) > 0:
                completed_tenders.append(tender)
                if len(completed_tenders) >= 5:
                    break

        if len(completed_tenders) < 5:
            print(f"   ⚠️  Found only {len(completed_tenders)} completed tenders")
            print("   This is normal - many tenders are still in progress")
            if len(completed_tenders) == 0:
                print("\n   💡 Try increasing date range for more completed tenders")
                return
        else:
            print(f"   ✅ Found 5 completed tenders")

        # Display tender summary
        print("\n   📋 Completed Tenders Found:")
        for i, tender in enumerate(completed_tenders[:5], 1):
            org_name = tender.get('orgaoEntidade', {}).get('razaoSocial', 'N/A')
            value = tender.get('valorTotalHomologado', 0)
            confidence = tender.get('medical_confidence', 0)
            control = tender.get('numeroControlePNCPCompra', 'N/A')

            print(f"\n   {i}. {org_name[:60]}")
            print(f"      Value: R$ {value:,.2f}")
            print(f"      Confidence: {confidence:.1f}%")
            print(f"      Control: {control}")

        # Process items for each tender
        print(f"\n4️⃣  Processing tender items ({len(completed_tenders[:5])} tenders)...")

        usd_to_brl = float(os.getenv('USD_TO_BRL_RATE', '5.0'))
        item_processor = ItemProcessor(
            api_client, product_matcher, db_ops, fernandes_products, usd_to_brl
        )

        total_items = 0
        total_medical_items = 0

        for i, tender in enumerate(completed_tenders[:5], 1):
            print(f"\n   Processing {i}/{len(completed_tenders[:5])}...")

            # Extract tender details
            cnpj = tender.get('cnpj', '')
            year = tender.get('ano') or tender.get('anoCompra')
            sequential = tender.get('sequencial') or tender.get('sequencialCompra')

            # Get tender ID from database (should exist from discovery)
            # For this quick test, we'll fetch items directly
            try:
                # Fetch items from API
                status, items_response = await api_client.get_tender_items(cnpj, year, sequential)

                if status == 200 and items_response:
                    items_list = items_response if isinstance(items_response, list) else items_response.get('items', [])
                    item_count = len(items_list)
                    total_items += item_count

                    # Count medical items (with CATMAT or medical keywords)
                    medical_count = 0
                    for item in items_list[:10]:  # Check first 10 items
                        desc = item.get('descricao', '').lower()
                        if any(keyword in desc for keyword in ['cateter', 'seringa', 'equipamento', 'hospitalar', 'cirúrgico', 'médico']):
                            medical_count += 1

                    total_medical_items += medical_count

                    print(f"      ✅ {item_count} items found, {medical_count} appear medical")

                    # Show sample items
                    if items_list:
                        print(f"      📦 Sample items:")
                        for item in items_list[:3]:
                            desc = item.get('descricao', 'N/A')[:60]
                            qty = item.get('quantidade', 0)
                            print(f"         - {desc}... (qty: {qty})")

                else:
                    print(f"      ⚠️  No items found (status: {status})")

            except Exception as e:
                print(f"      ❌ Error: {e}")
                logger.error(f"Error processing tender items: {e}")

        # Final summary
        print("\n" + "=" * 70)
        print("📊 QUICK TEST SUMMARY")
        print("=" * 70)
        print(f"⏱️  Total Time: {elapsed:.1f}s")
        print(f"📋 Medical Tenders Found: {len(medical_tenders)}")
        print(f"✅ Completed Tenders: {len(completed_tenders[:5])}")
        print(f"📦 Total Items: {total_items}")
        print(f"💊 Medical Items: {total_medical_items}")

        if total_items > 0:
            medical_rate = (total_medical_items / total_items) * 100
            print(f"🎯 Medical Item Rate: {medical_rate:.1f}%")

        print(f"\n🚀 API Efficiency: {metrics.total_api_calls} API calls")
        print(f"⚡ Speed: {len(medical_tenders) / max(elapsed, 1):.1f} tenders/second")

        print("\n✅ Quick test completed!")
        print("\n💡 To get more tenders:")
        print("   - Increase date range: 31 days → 60 days")
        print("   - Lower min_match_score: 40.0 → 30.0")
        print("   - Try different time periods (earlier months may have more completed tenders)")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        logger.error(f"Test failed: {e}", exc_info=True)
        raise

    finally:
        # Cleanup
        if api_client:
            await api_client.close_session()
        if db_manager:
            await db_manager.close()
            print("\n🔒 Connections closed")

if __name__ == "__main__":
    print("\n🚀 Starting quick SP test...")
    asyncio.run(quick_test())
