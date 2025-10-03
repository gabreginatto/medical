#!/usr/bin/env python3
"""
Show a sample of approved tenders with details
"""

import asyncio
import logging
import sys
import os
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from config import ProcessingConfig
from database import create_db_manager_from_env, DatabaseOperations
from pncp_api import PNCPAPIClient
from classifier import TenderClassifier
from optimized_discovery import OptimizedTenderDiscovery

# Configure logging
logging.basicConfig(
    level=logging.WARNING,  # Less verbose
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def show_tenders():
    """Quick discovery to show approved tenders"""

    print("=" * 80)
    print("FETCHING SAMPLE APPROVED TENDERS")
    print("=" * 80)

    # Quick configuration - smaller dataset
    config = ProcessingConfig(
        enabled_states=['SP'],
        min_tender_value=5_000.0,
        max_tender_value=2_000_000.0,
        min_match_score=40.0,
        allowed_modalities=[6],  # Just Pregão for speed
        use_org_cache=True,
        catmat_boost_enabled=True
    )

    # Short date range for speed
    end_date = datetime(2024, 9, 15)
    start_date = datetime(2024, 9, 1)  # Just 15 days

    start_date_str = start_date.strftime('%Y%m%d')
    end_date_str = end_date.strftime('%Y%m%d')

    print(f"\nDate Range: {start_date_str} to {end_date_str} (15 days)")
    print(f"State: São Paulo (SP)")
    print(f"Max tenders: 1000 (for speed)\n")

    api_client = None
    db_manager = None

    try:
        # Initialize components
        db_manager = create_db_manager_from_env()
        db_ops = DatabaseOperations(db_manager)

        api_client = PNCPAPIClient()
        await api_client.start_session()

        classifier = TenderClassifier()

        # Create discovery engine
        discovery_engine = OptimizedTenderDiscovery(api_client, classifier, db_ops, config)

        # Run discovery
        print("Running discovery...\n")
        medical_tenders, metrics = await discovery_engine.discover_medical_tenders_optimized(
            'SP', start_date_str, end_date_str
        )

        print(f"Found {len(medical_tenders)} medical tenders\n")

        # Group by approval method
        auto_approved = [t for t in medical_tenders if t.get('auto_approved')]
        sampled = [t for t in medical_tenders if not t.get('auto_approved')]

        print("=" * 80)
        print(f"APPROVAL BREAKDOWN")
        print("=" * 80)
        print(f"Auto-approved (Phase 1): {len(auto_approved)}")
        print(f"Sampled (Phase 2): {len(sampled)}")
        print()

        # Show auto-approved reasons
        if auto_approved:
            reasons = {}
            for t in auto_approved:
                reason = t.get('approval_reason', 'unknown')
                reasons[reason] = reasons.get(reason, 0) + 1

            print("Auto-approval reasons:")
            for reason, count in sorted(reasons.items(), key=lambda x: -x[1])[:5]:
                print(f"  {reason}: {count}")
            print()

        # Show AUTO-APPROVED tenders
        print("=" * 80)
        print("AUTO-APPROVED TENDERS (Phase 1 - No API Sampling)")
        print("=" * 80)
        for i, tender in enumerate(auto_approved[:10], 1):
            org = tender.get('orgaoEntidade', {}).get('razaoSocial', 'N/A')
            obj = tender.get('objetoCompra', 'N/A')
            value = tender.get('valorTotalHomologado', 0) or tender.get('valorTotalEstimado', 0)
            conf = tender.get('medical_confidence', 0)
            reason = tender.get('approval_reason', 'N/A')

            print(f"\n{i}. {org}")
            print(f"   Object: {obj[:100]}{'...' if len(obj) > 100 else ''}")
            print(f"   Value: R$ {value:,.2f}")
            print(f"   Confidence: {conf}%")
            print(f"   Reason: {reason}")

        # Show SAMPLED tenders
        print("\n" + "=" * 80)
        print("SAMPLED TENDERS (Phase 2 - Required API Verification)")
        print("=" * 80)
        for i, tender in enumerate(sampled[:10], 1):
            org = tender.get('orgaoEntidade', {}).get('razaoSocial', 'N/A')
            obj = tender.get('objetoCompra', 'N/A')
            value = tender.get('valorTotalHomologado', 0) or tender.get('valorTotalEstimado', 0)
            conf = tender.get('medical_confidence', 0)

            print(f"\n{i}. {org}")
            print(f"   Object: {obj[:100]}{'...' if len(obj) > 100 else ''}")
            print(f"   Value: R$ {value:,.2f}")
            print(f"   Confidence: {conf}%")

        print("\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print(f"Total medical tenders: {len(medical_tenders)}")
        print(f"Auto-approved (instant): {len(auto_approved)} ({len(auto_approved)/max(len(medical_tenders),1)*100:.1f}%)")
        print(f"Required sampling: {len(sampled)} ({len(sampled)/max(len(medical_tenders),1)*100:.1f}%)")
        print(f"API calls saved: {len(auto_approved)}")
        print()

    except Exception as e:
        print(f"\n❌ Error: {e}")
        logger.error(f"Error: {e}", exc_info=True)
        raise

    finally:
        # Cleanup
        if api_client:
            await api_client.close_session()
        if db_manager:
            await db_manager.close()

if __name__ == "__main__":
    asyncio.run(show_tenders())
