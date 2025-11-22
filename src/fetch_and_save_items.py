#!/usr/bin/env python3
"""
Fetch items for all tenders in the database and save them
"""

import asyncio
import logging
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

from .database import create_db_manager_from_env, DatabaseOperations
from .pncp_api import PNCPAPIClient

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def fetch_and_save_items():
    """Fetch items for all tenders in database and save them"""

    logger.info("=" * 70)
    logger.info("📦 FETCH AND SAVE TENDER ITEMS")
    logger.info("=" * 70)

    db_manager = None
    api_client = None
    start_time = datetime.now()

    try:
        # Initialize
        logger.info("")
        logger.info("1️⃣  Initializing...")
        db_manager = create_db_manager_from_env()
        db_ops = DatabaseOperations(db_manager)

        api_client = PNCPAPIClient(max_concurrent_requests=5)
        await api_client.start_session()
        logger.info("✅ Initialized")

        # Get tenders that don't have items yet (unprocessed)
        logger.info("")
        logger.info("2️⃣  Fetching unprocessed tenders from database...")
        tenders = await db_ops.get_unprocessed_tenders()
        logger.info(f"✅ Found {len(tenders)} tenders without items")

        if len(tenders) == 0:
            logger.info("No tenders to process. Exiting.")
            return

        # Process each tender
        logger.info("")
        logger.info("3️⃣  Fetching items from PNCP API...")
        total_items = 0
        tenders_with_items = 0
        tenders_without_items = 0
        failed_tenders = 0

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
                    failed_tenders += 1
                    continue

                # Fetch items from API (returns tuple: status, data)
                status, response = await api_client.get_tender_items(cnpj, year, sequential)

                # Check status
                if status != 200:
                    logger.warning(f"Tender {control_num}: API returned status {status}")
                    tenders_without_items += 1
                    continue

                # Extract items list from response
                if isinstance(response, list):
                    items_list = response
                elif isinstance(response, dict):
                    items_list = response.get('data', [])
                else:
                    logger.error(f"Tender {control_num}: Unexpected response type {type(response)}")
                    failed_tenders += 1
                    continue

                if not items_list:
                    tenders_without_items += 1
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
                        'description': item.get('descricao', ''),  # Item name/description
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
                    total_items += len(items_data)
                    tenders_with_items += 1

                # Progress logging every 10 tenders
                if i % 10 == 0:
                    elapsed = (datetime.now() - start_time).total_seconds()
                    rate = i / elapsed if elapsed > 0 else 0
                    remaining = len(tenders) - i
                    eta = remaining / rate if rate > 0 else 0

                    logger.info(f"Progress: {i}/{len(tenders)} tenders ({i/len(tenders)*100:.1f}%) | "
                               f"Items: {total_items} | "
                               f"Rate: {rate:.2f} tenders/sec | "
                               f"ETA: {eta/60:.1f} min")

                # Checkpoint every 50 tenders
                if i % 50 == 0:
                    logger.info(f"📊 Checkpoint - With items: {tenders_with_items}, "
                               f"Without items: {tenders_without_items}, "
                               f"Failed: {failed_tenders}")

            except Exception as e:
                logger.error(f"Error processing tender {control_num}: {e}")
                failed_tenders += 1
                continue

        logger.info("")
        logger.info("✅ Item fetching complete")

        # Summary
        elapsed_total = (datetime.now() - start_time).total_seconds()
        logger.info("")
        logger.info("=" * 70)
        logger.info("📊 SUMMARY")
        logger.info("=" * 70)
        logger.info(f"Total Tenders Processed: {len(tenders)}")
        logger.info(f"Tenders with Items: {tenders_with_items}")
        logger.info(f"Tenders without Items: {tenders_without_items}")
        logger.info(f"Failed Tenders: {failed_tenders}")
        logger.info(f"Total Items Saved: {total_items}")

        if tenders_with_items > 0:
            avg_items = total_items / tenders_with_items
            logger.info(f"Average Items per Tender: {avg_items:.1f}")

        logger.info(f"Total Time: {elapsed_total/60:.1f} minutes")
        logger.info(f"Average Rate: {len(tenders)/elapsed_total:.2f} tenders/sec")
        logger.info("")
        logger.info("✅ All items saved to database!")

    except Exception as e:
        logger.error(f"❌ Error: {e}", exc_info=True)
        raise

    finally:
        if api_client:
            await api_client.close_session()
        if db_manager:
            await db_manager.close()
            logger.info("")
            logger.info("🔒 Connections closed")

if __name__ == "__main__":
    asyncio.run(fetch_and_save_items())
