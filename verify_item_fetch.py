#!/usr/bin/env python3
"""
Simple script to verify if item fetch failures are real or API call issues
Tests 10 failed tenders + 10 auto-approved tenders (control group)
"""

import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from pncp_api import PNCPAPIClient

# Configure logging to both console and file
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('verify_item_fetch.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 10 tenders that FAILED to fetch items (got 404)
FAILED_TENDERS = [
    ("24082016000159", "2024", "88"),
    ("46374500000194", "2024", "3601"),
    ("46374500000194", "2024", "3558"),
    ("46374500000194", "2024", "3603"),
    ("12474705000120", "2024", "106"),
    ("46374500000194", "2024", "3616"),
    ("46374500000194", "2024", "3615"),
    ("46374500000194", "2024", "3621"),
    ("46374500000194", "2024", "3640"),
    ("60448040000122", "2024", "193"),
]

# 10 auto-approved tenders (should have items, from previous successful run)
# Convert from control number format: "CNPJ-1-SEQSEQ/YEAR" -> (CNPJ, YEAR, SEQ)
CONTROL_TENDERS = [
    ("60448040000122", "2024", "186"),
    ("11892520000172", "2024", "42"),
    ("12474705000120", "2024", "130"),
    ("00394502000144", "2025", "84"),
    ("58200015000183", "2024", "158"),
    ("45227337000174", "2024", "58"),
    ("60747318000162", "2024", "172"),
    ("46374500000194", "2024", "3558"),  # Same as failed - interesting!
    ("46374500000194", "2024", "3725"),
    ("46374500000194", "2024", "3827"),
]

async def test_item_fetch():
    """Test fetching items for both groups"""

    logger.info("=" * 70)
    logger.info("ITEM FETCH VERIFICATION TEST")
    logger.info("=" * 70)
    logger.info("Testing if 404s are real (no items) or API call errors")

    api_client = PNCPAPIClient(max_concurrent_requests=5)
    await api_client.start_session()

    try:
        # Test failed tenders
        logger.info("=" * 70)
        logger.info("GROUP 1: Tenders that FAILED (404) in main test")
        logger.info("=" * 70)
        logger.info("Expected: Most/all should fail again (confirming no items exist)")

        failed_successes = 0
        failed_failures = 0

        for i, (cnpj, year, seq) in enumerate(FAILED_TENDERS, 1):
            try:
                logger.info(f"Testing failed tender {i}/10: {cnpj}/{year}/{seq}")
                status, response = await api_client.get_tender_items(cnpj, year, seq)

                if status == 200 and response:
                    items = response if isinstance(response, list) else response.get('items', [])
                    item_count = len(items)
                    failed_successes += 1
                    logger.info(f"  ✅ SUCCESS! {cnpj}/{year}/{seq} - {item_count} items found")
                    print(f"{i:2}. ✅ {cnpj}/{year}/{seq:>4} - SUCCESS! {item_count} items")
                else:
                    failed_failures += 1
                    logger.warning(f"  ❌ FAILED: {cnpj}/{year}/{seq} - status {status}")
                    print(f"{i:2}. ❌ {cnpj}/{year}/{seq:>4} - FAILED (status: {status})")
            except Exception as e:
                failed_failures += 1
                logger.error(f"  ❌ ERROR: {cnpj}/{year}/{seq} - {e}")
                print(f"{i:2}. ❌ {cnpj}/{year}/{seq:>4} - ERROR: {e}")

        # Test control group (auto-approved tenders)
        logger.info("=" * 70)
        logger.info("GROUP 2: Auto-approved tenders (CONTROL - should work)")
        logger.info("=" * 70)
        logger.info("Expected: Most/all should succeed (confirming API calls work)")

        control_successes = 0
        control_failures = 0

        for i, (cnpj, year, seq) in enumerate(CONTROL_TENDERS, 1):
            try:
                logger.info(f"Testing control tender {i}/10: {cnpj}/{year}/{seq}")
                status, response = await api_client.get_tender_items(cnpj, year, seq)

                if status == 200 and response:
                    items = response if isinstance(response, list) else response.get('items', [])
                    item_count = len(items)
                    control_successes += 1
                    logger.info(f"  ✅ SUCCESS! {cnpj}/{year}/{seq} - {item_count} items found")
                    print(f"{i:2}. ✅ {cnpj}/{year}/{seq:>4} - SUCCESS! {item_count} items")
                else:
                    control_failures += 1
                    logger.warning(f"  ❌ FAILED: {cnpj}/{year}/{seq} - status {status}")
                    print(f"{i:2}. ❌ {cnpj}/{year}/{seq:>4} - FAILED (status: {status})")
            except Exception as e:
                control_failures += 1
                logger.error(f"  ❌ ERROR: {cnpj}/{year}/{seq} - {e}")
                print(f"{i:2}. ❌ {cnpj}/{year}/{seq:>4} - ERROR: {e}")

        # Summary
        logger.info("=" * 70)
        logger.info("SUMMARY")
        logger.info("=" * 70)
        logger.info(f"Group 1 (Failed in main test):")
        logger.info(f"  ✅ Successes: {failed_successes}/10 ({failed_successes*10}%)")
        logger.info(f"  ❌ Failures:  {failed_failures}/10 ({failed_failures*10}%)")

        logger.info(f"Group 2 (Control - auto-approved):")
        logger.info(f"  ✅ Successes: {control_successes}/10 ({control_successes*10}%)")
        logger.info(f"  ❌ Failures:  {control_failures}/10 ({control_failures*10}%)")

        logger.info("=" * 70)
        logger.info("DIAGNOSIS")
        logger.info("=" * 70)

        if control_successes >= 8:
            logger.info("✅ API calls are working correctly (control group mostly succeeded)")
            if failed_failures >= 8:
                logger.info("✅ 404s are REAL - those tenders genuinely have no item data")
                logger.info("💡 CONCLUSION: The PNCP API data quality for July-Sept 2024 is poor.")
                logger.info("   Recommendation: Try a different date range with better data.")
            else:
                logger.warning("⚠️  Unexpected: Failed tenders now work!")
                logger.warning("   Possible timing/caching issue with PNCP API.")
        else:
            logger.error("❌ API calls are NOT working correctly (control group failed)")
            logger.error("   Our get_tender_items() calls may have bugs.")
            logger.error("   Check the API endpoint, parameters, or authentication.")

        logger.info("=" * 70)

        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)
        print(f"\nGroup 1 (Failed): {failed_successes}/10 success, {failed_failures}/10 failed")
        print(f"Group 2 (Control): {control_successes}/10 success, {control_failures}/10 failed")
        print("\nFull details saved to: verify_item_fetch.log")
        print("=" * 70)

    finally:
        await api_client.close_session()

if __name__ == "__main__":
    start_time = datetime.now()
    logger.info("🚀 Starting verification test...")
    logger.info(f"Start time: {start_time}")
    print("\n🚀 Starting verification test...")
    print(f"Logging to: verify_item_fetch.log\n")

    try:
        asyncio.run(test_item_fetch())
    finally:
        end_time = datetime.now()
        elapsed = (end_time - start_time).total_seconds()
        logger.info(f"Test completed in {elapsed:.1f}s")
        print(f"\n✅ Test completed in {elapsed:.1f}s")
