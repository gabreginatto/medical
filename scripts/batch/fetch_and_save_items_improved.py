#!/usr/bin/env python3
"""
Fetch items for all tenders in the database and save them
IMPROVED VERSION: Processes ALL unprocessed tenders in batches
"""

import asyncio
import logging
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

from src.database import create_db_manager_from_env, DatabaseOperations
from src.pncp_api import PNCPAPIClient

# Logger will be configured by setup_logging()
logger = logging.getLogger(__name__)


def setup_logging():
    """Setup logging with timestamped file (similar to main.py)"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_filename = f'logs/item_extraction_{timestamp}.log'

    # Create logs directory if it doesn't exist
    os.makedirs('logs', exist_ok=True)

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_filename),
            logging.StreamHandler()
        ],
        force=True  # Override any existing config
    )

    logger.info("=" * 70)
    logger.info(f"📝 Log file: {log_filename}")
    logger.info("=" * 70)

    return log_filename

async def fetch_and_save_items(batch_size: int = None, max_batches: int = None):
    """
    Fetch items for all tenders in database and save them

    Args:
        batch_size: Number of tenders to process per batch (default: 500, or from env)
        max_batches: Maximum number of batches to process (default: 10, use 0 for unlimited)
    """

    # Get batch size from environment or use default
    if batch_size is None:
        batch_size = int(os.getenv('ITEM_FETCH_BATCH_SIZE', '500'))

    # Get max_batches from environment or use default of 10
    if max_batches is None:
        max_batches = int(os.getenv('ITEM_FETCH_MAX_BATCHES', '10'))

    # 0 or negative means unlimited
    if max_batches <= 0:
        max_batches = None

    logger.info("")
    logger.info("=" * 70)
    logger.info("📦 FETCH AND SAVE TENDER ITEMS - IMPROVED VERSION")
    logger.info("=" * 70)
    logger.info(f"Batch size: {batch_size} tenders per batch")
    if max_batches:
        logger.info(f"Max batches: {max_batches} batches per run")
        logger.info(f"Total tenders per run: ~{batch_size * max_batches:,}")
    else:
        logger.info(f"Max batches: Unlimited (will process ALL unprocessed tenders)")
    logger.info("=" * 70)

    db_manager = None
    api_client = None
    start_time = datetime.now()

    try:
        # Initialize
        logger.info("")
        logger.info("1️⃣  INITIALIZATION")
        logger.info("-" * 70)
        db_manager = create_db_manager_from_env()
        db_ops = DatabaseOperations(db_manager)

        api_client = PNCPAPIClient(max_concurrent_requests=5)
        await api_client.start_session()
        logger.info("✅ Database and API client initialized")

        # Get total count of unprocessed tenders
        logger.info("")
        logger.info("2️⃣  CHECKING UNPROCESSED TENDERS")
        logger.info("-" * 70)
        conn = await db_manager.get_connection()
        try:
            total_unprocessed = await conn.fetchval("""
                SELECT COUNT(DISTINCT t.id)
                FROM tenders t
                LEFT JOIN tender_items ti ON t.id = ti.tender_id
                WHERE t.total_homologated_value > 0
                  AND ti.tender_id IS NULL
            """)
        finally:
            await conn.close()

        logger.info(f"✅ Found {total_unprocessed:,} tenders without items")

        if total_unprocessed == 0:
            logger.info("")
            logger.info("✅ All tenders already have items extracted!")
            return

        # Process in batches until all are done
        logger.info("")
        logger.info("3️⃣  PROCESSING TENDERS IN BATCHES")
        logger.info("-" * 70)
        logger.info(f"Starting batch processing at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("")

        total_processed = 0
        total_items_saved = 0
        total_with_items = 0
        total_without_items = 0
        total_failed = 0
        batch_num = 0

        while True:
            batch_num += 1

            # Check if we've reached max_batches limit
            if max_batches and batch_num > max_batches:
                logger.info("")
                logger.info(f"⚠️  Reached maximum batch limit ({max_batches})")
                break

            logger.info("=" * 70)
            logger.info(f"📦 BATCH {batch_num}")
            logger.info("=" * 70)

            # Get next batch of unprocessed tenders
            tenders = await db_ops.get_unprocessed_tenders(limit=batch_size)

            if not tenders:
                logger.info("✅ No more tenders to process!")
                break

            batch_start = datetime.now()
            logger.info(f"Processing {len(tenders)} tenders from database...")
            logger.info(f"Batch start time: {batch_start.strftime('%Y-%m-%d %H:%M:%S')}")

            # Process each tender in batch
            batch_items = 0
            batch_with_items = 0
            batch_without_items = 0
            batch_failed = 0

            for i, tender in enumerate(tenders, 1):
                tender_id = tender['id']
                cnpj = tender['cnpj']
                year = tender['year']
                sequential = tender['sequential_number']
                control_num = tender.get('control_number', f"tender_{tender_id}")

                try:
                    # Skip if year or sequential is None
                    if year is None or sequential is None:
                        logger.warning(f"Tender {control_num}: Missing year ({year}) or sequential ({sequential}), skipping")
                        batch_failed += 1
                        continue

                    # Fetch items from API (returns tuple: status, data)
                    status, response = await api_client.get_tender_items(cnpj, year, sequential)

                    # Check status
                    if status != 200:
                        logger.warning(f"Tender {control_num}: API returned status {status}")
                        batch_without_items += 1
                        continue

                    # Extract items list from response
                    if isinstance(response, list):
                        items_list = response
                    elif isinstance(response, dict):
                        items_list = response.get('data', [])
                    else:
                        logger.error(f"Tender {control_num}: Unexpected response type {type(response)}")
                        batch_failed += 1
                        continue

                    if not items_list:
                        batch_without_items += 1
                        if i % 50 == 0:
                            logger.info(f"   Progress: {i}/{len(tenders)} tenders processed in batch {batch_num}...")
                        continue

                    # Process items for database
                    items_data = []
                    for item in items_list:
                        # Debug: Check item type
                        if not isinstance(item, dict):
                            logger.error(f"Tender {control_num}: Item is {type(item).__name__} not dict: {item}")
                            continue

                        # Extract CATMAT codes
                        catmat_codes = []
                        if 'codigoCatmat' in item and item['codigoCatmat']:
                            catmat_codes.append(str(item['codigoCatmat']))

                        # Initialize item data with basic info
                        item_data = {
                            'tender_id': tender_id,
                            'item_number': item.get('numeroItem', 0),
                            'description': item.get('descricao', ''),
                            'unit': item.get('unidadeMedida', ''),
                            'quantity': item.get('quantidade'),
                            'estimated_unit_value': item.get('valorUnitarioEstimado'),
                            'estimated_total_value': item.get('valorTotal'),
                            'homologated_unit_value': None,
                            'homologated_total_value': None,
                            'winner_name': None,
                            'winner_cnpj': None,
                            'catmat_codes': catmat_codes,
                            'has_medical_catmat': len(catmat_codes) > 0,
                            'catmat_score_boost': 10 if len(catmat_codes) > 0 else 0,
                            'sample_analyzed': False,
                            'medical_confidence_score': None
                        }

                        # If item has results, fetch homologated prices
                        if item.get('temResultado', False):
                            try:
                                result_status, result_response = await api_client.get_item_results(
                                    cnpj, year, sequential, item_data['item_number']
                                )

                                if result_status == 200 and isinstance(result_response, list) and len(result_response) > 0:
                                    # Use first result (winner)
                                    result = result_response[0]
                                    item_data['homologated_unit_value'] = result.get('valorUnitarioHomologado')
                                    item_data['homologated_total_value'] = result.get('valorTotalHomologado')
                                    item_data['winner_name'] = result.get('nomeRazaoSocialFornecedor')
                                    item_data['winner_cnpj'] = result.get('niFornecedor')
                            except Exception as e:
                                logger.warning(f"Could not fetch results for item {item_data['item_number']}: {e}")

                        items_data.append(item_data)

                    # Save items to database
                    if items_data:
                        await db_ops.insert_tender_items_batch(items_data)
                        batch_items += len(items_data)
                        batch_with_items += 1

                    if i % 50 == 0:
                        logger.info(f"   Progress: {i}/{len(tenders)} tenders, {batch_items} items saved in batch {batch_num}...")

                except Exception as e:
                    logger.error(f"Error processing tender {control_num}: {e}")
                    batch_failed += 1
                    continue

            # Update totals
            total_processed += len(tenders)
            total_items_saved += batch_items
            total_with_items += batch_with_items
            total_without_items += batch_without_items
            total_failed += batch_failed

            batch_time = (datetime.now() - batch_start).total_seconds()
            tenders_per_sec = len(tenders) / batch_time if batch_time > 0 else 0

            # Batch summary
            logger.info("")
            logger.info(f"✅ Batch {batch_num} complete:")
            logger.info(f"   • Tenders processed: {len(tenders)}")
            logger.info(f"   • Items saved: {batch_items}")
            logger.info(f"   • Tenders with items: {batch_with_items}")
            logger.info(f"   • Tenders without items: {batch_without_items}")
            logger.info(f"   • Failed: {batch_failed}")
            logger.info(f"   • Time: {batch_time:.1f}s ({tenders_per_sec:.1f} tenders/sec)")
            logger.info(f"   • Overall progress: {total_processed}/{total_unprocessed} ({total_processed/total_unprocessed*100:.1f}%)")

            # Estimate remaining time
            remaining = total_unprocessed - total_processed
            if remaining > 0 and tenders_per_sec > 0:
                est_remaining_sec = remaining / tenders_per_sec
                est_remaining_min = est_remaining_sec / 60
                logger.info(f"   • Estimated time remaining: {est_remaining_min:.1f} minutes ({est_remaining_min/60:.1f} hours)")

            logger.info("")

            # If batch is smaller than batch_size, we're done
            if len(tenders) < batch_size:
                logger.info("✅ All tenders processed!")
                break

        # Final summary
        total_time = (datetime.now() - start_time).total_seconds()
        end_time = datetime.now()

        # Check if there are still unprocessed tenders
        conn = await db_manager.get_connection()
        try:
            remaining_unprocessed = await conn.fetchval("""
                SELECT COUNT(DISTINCT t.id)
                FROM tenders t
                LEFT JOIN tender_items ti ON t.id = ti.tender_id
                WHERE t.total_homologated_value > 0
                  AND ti.tender_id IS NULL
            """)
        finally:
            await conn.close()

        logger.info("")
        logger.info("=" * 70)
        logger.info("📊 FINAL SUMMARY")
        logger.info("=" * 70)
        logger.info(f"Start time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"End time: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"Total Batches: {batch_num}")
        logger.info(f"Total Tenders Processed: {total_processed:,}")
        logger.info(f"Total Items Saved: {total_items_saved:,}")
        logger.info(f"Tenders with Items: {total_with_items:,} ({total_with_items/total_processed*100:.1f}%)")
        logger.info(f"Tenders without Items: {total_without_items:,} ({total_without_items/total_processed*100:.1f}%)")
        logger.info(f"Failed Tenders: {total_failed:,} ({total_failed/total_processed*100:.1f}%)")
        logger.info(f"Total Time: {total_time:.1f}s ({total_time/60:.1f} minutes / {total_time/3600:.1f} hours)")

        if total_with_items > 0:
            avg_items = total_items_saved / total_with_items
            logger.info(f"Average Items per Tender: {avg_items:.1f}")

        if total_processed > 0:
            avg_time_per_tender = total_time / total_processed
            logger.info(f"Average Time per Tender: {avg_time_per_tender:.2f}s")

        logger.info("")
        logger.info(f"Remaining unprocessed tenders: {remaining_unprocessed:,}")

        if remaining_unprocessed > 0:
            estimated_batches = (remaining_unprocessed // batch_size) + (1 if remaining_unprocessed % batch_size else 0)
            logger.info(f"Estimated batches needed: {estimated_batches}")
            logger.info("")
            logger.info("⚠️  There are still tenders without items!")
            logger.info("   Run this script again to process the next batch.")
            logger.info(f"   Command: python3 fetch_and_save_items_improved.py")
        else:
            logger.info("")
            logger.info("✅ All tenders have items extracted!")

        logger.info("=" * 70)

    except Exception as e:
        logger.error("")
        logger.error("=" * 70)
        logger.error("❌ ITEM EXTRACTION FAILED")
        logger.error("=" * 70)
        logger.error(f"Error: {e}", exc_info=True)
        raise

    finally:
        if api_client:
            await api_client.close_session()
        if db_manager:
            await db_manager.close()
        logger.info("")
        logger.info("🔒 Connections closed")

if __name__ == "__main__":
    import sys

    # Setup logging first
    log_file = setup_logging()

    # Parse command line arguments
    # Usage: python3 fetch_and_save_items_improved.py [batch_size] [max_batches]
    # Examples:
    #   python3 fetch_and_save_items_improved.py           # Default: 500 per batch, 10 batches max
    #   python3 fetch_and_save_items_improved.py 1000      # 1000 per batch, 10 batches max
    #   python3 fetch_and_save_items_improved.py 500 20    # 500 per batch, 20 batches max
    #   python3 fetch_and_save_items_improved.py 500 0     # 500 per batch, unlimited (process all)

    batch_size = int(sys.argv[1]) if len(sys.argv) > 1 else None
    max_batches = int(sys.argv[2]) if len(sys.argv) > 2 else None

    try:
        asyncio.run(fetch_and_save_items(batch_size, max_batches))
        logger.info("")
        logger.info(f"📝 Full log saved to: {log_file}")
    except KeyboardInterrupt:
        logger.info("")
        logger.info("⚠️  Process interrupted by user")
        logger.info(f"📝 Partial log saved to: {log_file}")
    except Exception as e:
        logger.error("")
        logger.error(f"📝 Error log saved to: {log_file}")
        raise
