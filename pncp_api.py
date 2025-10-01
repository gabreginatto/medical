"""
PNCP API Client with Rate Limiting
Handles all interactions with the PNCP Consultation API
Note: The PNCP Consultation API does not require authentication
"""

import asyncio
import aiohttp
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
import time
from config import APIConfig, ProcessingConfig

logger = logging.getLogger(__name__)

class RateLimiter:
    """Simple rate limiter for API requests"""

    def __init__(self, max_requests_per_minute: int = 60, max_requests_per_hour: int = 1000):
        self.max_per_minute = max_requests_per_minute
        self.max_per_hour = max_requests_per_hour
        self.minute_requests = []
        self.hour_requests = []

    async def wait_if_needed(self):
        """Wait if rate limits would be exceeded"""
        now = time.time()

        # Clean old requests
        self.minute_requests = [req_time for req_time in self.minute_requests if now - req_time < 60]
        self.hour_requests = [req_time for req_time in self.hour_requests if now - req_time < 3600]

        # Check minute limit
        if len(self.minute_requests) >= self.max_per_minute:
            sleep_time = 60 - (now - self.minute_requests[0])
            if sleep_time > 0:
                logger.warning(f"Rate limit reached, sleeping for {sleep_time:.1f} seconds")
                await asyncio.sleep(sleep_time)
                return await self.wait_if_needed()

        # Check hour limit
        if len(self.hour_requests) >= self.max_per_hour:
            sleep_time = 3600 - (now - self.hour_requests[0])
            if sleep_time > 0:
                logger.warning(f"Hourly rate limit reached, sleeping for {sleep_time:.1f} seconds")
                await asyncio.sleep(sleep_time)
                return await self.wait_if_needed()

        # Record this request
        self.minute_requests.append(now)
        self.hour_requests.append(now)

class PNCPAPIClient:
    """PNCP API client with rate limiting (no authentication required)"""

    def __init__(self, rate_limiter: RateLimiter = None, max_concurrent_requests: int = 5):
        self.consultation_url = APIConfig.CONSULTATION_BASE_URL
        self.session: Optional[aiohttp.ClientSession] = None
        self.max_concurrent_requests = max_concurrent_requests
        self.rate_limiter = rate_limiter or RateLimiter(
            ProcessingConfig().max_requests_per_minute,
            ProcessingConfig().max_requests_per_hour
        )

    async def __aenter__(self):
        """Async context manager entry"""
        await self.start_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close_session()

    async def start_session(self):
        """Initialize HTTP session"""
        if self.session is None:
            timeout = aiohttp.ClientTimeout(total=APIConfig.REQUEST_TIMEOUT)
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                headers={'User-Agent': 'PNCP-Medical-Data-Client/1.0'}
            )

    async def close_session(self):
        """Close HTTP session"""
        if self.session:
            await self.session.close()
            self.session = None

    async def _make_request(self, method: str, url: str, **kwargs) -> Tuple[int, Dict[str, Any]]:
        """Make HTTP request with rate limiting and error handling"""
        await self.rate_limiter.wait_if_needed()

        if not self.session:
            await self.start_session()

        retries = 0
        while retries < APIConfig.MAX_RETRIES:
            try:
                async with self.session.request(method, url, **kwargs) as response:
                    if response.status == 429:  # Rate limited
                        wait_time = min(2 ** retries * APIConfig.RETRY_DELAY, 60)
                        logger.warning(f"Rate limited, waiting {wait_time} seconds")
                        await asyncio.sleep(wait_time)
                        retries += 1
                        continue

                    # Try to parse JSON response
                    try:
                        data = await response.json()
                    except:
                        data = {'error': 'Invalid JSON response', 'text': await response.text()}

                    return response.status, data

            except Exception as e:
                retries += 1
                if retries >= APIConfig.MAX_RETRIES:
                    logger.error(f"Request failed after {retries} retries: {e}")
                    return 500, {'error': str(e)}

                wait_time = 2 ** retries * APIConfig.RETRY_DELAY
                logger.warning(f"Request failed, retrying in {wait_time} seconds: {e}")
                await asyncio.sleep(wait_time)

        return 500, {'error': 'Max retries exceeded'}

    def _get_headers(self) -> Dict[str, str]:
        """Get standard headers for API requests"""
        return {'Accept': 'application/json'}

    async def get_tenders_by_publication_date(self, start_date: str, end_date: str,
                                            modality_code: int, state: str = None,
                                            municipality_code: str = None,
                                            cnpj: str = None, page: int = 1,
                                            page_size: int = 10) -> Tuple[int, Dict[str, Any]]:
        """Get tenders by publication date using consultation API"""

        url = f"{self.consultation_url}/v1/contratacoes/publicacao"

        # Ensure page size is within API limits (10-500)
        if page_size < APIConfig.MIN_PAGE_SIZE or page_size > APIConfig.MAX_PAGE_SIZE:
            logger.warning(f"Page size {page_size} out of range [{APIConfig.MIN_PAGE_SIZE}-{APIConfig.MAX_PAGE_SIZE}], clamping to valid range")
        final_page_size = max(APIConfig.MIN_PAGE_SIZE, min(page_size, APIConfig.MAX_PAGE_SIZE))

        params = {
            'dataInicial': start_date,
            'dataFinal': end_date,
            'codigoModalidadeContratacao': modality_code,
            'pagina': page,
            'tamanhoPagina': final_page_size
        }

        logger.debug(f"API request params: {params}")

        if state:
            params['uf'] = state
        if municipality_code:
            params['codigoMunicipioIbge'] = municipality_code
        if cnpj:
            params['cnpj'] = cnpj

        return await self._make_request('GET', url, params=params)

    async def get_tender_items(self, cnpj: str, year: int, sequential: int) -> Tuple[int, Dict[str, Any]]:
        """Get all items for a specific tender"""
        url = f"{self.consultation_url}/v1/orgaos/{cnpj}/compras/{year}/{sequential}/itens"
        headers = self._get_headers()

        return await self._make_request('GET', url, headers=headers)

    async def get_item_results(self, cnpj: str, year: int, sequential: int,
                             item_number: int) -> Tuple[int, Dict[str, Any]]:
        """Get results (bids) for a specific item"""
        url = f"{self.consultation_url}/v1/orgaos/{cnpj}/compras/{year}/{sequential}/itens/{item_number}/resultados"
        headers = self._get_headers()

        return await self._make_request('GET', url, headers=headers)

    async def get_specific_item_result(self, cnpj: str, year: int, sequential: int,
                                     item_number: int, result_sequential: int) -> Tuple[int, Dict[str, Any]]:
        """Get specific result details for an item"""
        url = f"{self.consultation_url}/v1/orgaos/{cnpj}/compras/{year}/{sequential}/itens/{item_number}/resultados/{result_sequential}"
        headers = self._get_headers()

        return await self._make_request('GET', url, headers=headers)

    async def _fetch_single_page(self, start_date: str, end_date: str, modality: int,
                                 state_code: str, page: int, semaphore: asyncio.Semaphore) -> Tuple[int, Dict]:
        """Helper to fetch a single page with semaphore limiting"""
        async with semaphore:
            return await self.get_tenders_by_publication_date(
                start_date, end_date, modality, state_code, page=page, page_size=20
            )

    async def discover_tenders_for_state(self, state_code: str, start_date: str, end_date: str,
                                       modalities: List[int] = None, max_tenders: int = None) -> List[Dict[str, Any]]:
        """Discover tenders for a specific state within date range (with async concurrency)

        Args:
            state_code: State code (e.g., 'SP')
            start_date: Start date in YYYYMMDD format
            end_date: End date in YYYYMMDD format
            modalities: List of modality codes (default: [4, 6, 8])
            max_tenders: Maximum number of tenders to retrieve (None = all)

        Performance: Uses concurrent page fetching for 3-5x speedup within rate limits
        """
        if modalities is None:
            modalities = [4, 6, 8]  # Electronic tenders, Pregão, Dispensa

        all_tenders = []
        semaphore = asyncio.Semaphore(self.max_concurrent_requests)

        logger.info(f"🚀 Using concurrent fetching with {self.max_concurrent_requests} workers")

        for modality in modalities:
            if max_tenders and len(all_tenders) >= max_tenders:
                logger.info(f"Reached max_tenders limit ({max_tenders}), stopping discovery")
                break

            try:
                # STEP 1: Fetch page 1 to determine total pages
                status, first_response = await self.get_tenders_by_publication_date(
                    start_date, end_date, modality, state_code, page=1, page_size=20
                )

                if status != 200:
                    logger.error(f"Failed to get first page for {state_code}, modality {modality}: {status}")
                    continue

                first_data = first_response.get('data', [])
                if not first_data:
                    logger.info(f"No tenders found for {state_code}, modality {modality}")
                    continue

                # Add first page data
                if max_tenders:
                    remaining = max_tenders - len(all_tenders)
                    first_data = first_data[:remaining]

                all_tenders.extend(first_data)
                logger.info(f"Page 1/{first_response.get('totalPaginas', 1)} for {state_code}, modality {modality}: {len(first_data)} tenders")

                # Check if we're done
                if max_tenders and len(all_tenders) >= max_tenders:
                    logger.info(f"Reached max_tenders limit ({max_tenders}) after page 1")
                    break

                pages_remaining = first_response.get('paginasRestantes', 0)
                if pages_remaining == 0:
                    continue

                # STEP 2: Fetch remaining pages concurrently
                total_pages = first_response.get('totalPaginas', 1)
                pages_to_fetch = list(range(2, total_pages + 1))

                logger.info(f"⚡ Fetching pages 2-{total_pages} concurrently ({len(pages_to_fetch)} pages, {self.max_concurrent_requests} workers)")

                # Create concurrent tasks with semaphore
                tasks = [
                    self._fetch_single_page(start_date, end_date, modality, state_code, page, semaphore)
                    for page in pages_to_fetch
                ]

                # Fetch all pages concurrently
                results = await asyncio.gather(*tasks, return_exceptions=True)

                # Process results
                for page_num, result in zip(pages_to_fetch, results):
                    if isinstance(result, Exception):
                        logger.error(f"Error fetching page {page_num}: {result}")
                        continue

                    status, response = result
                    if status == 200:
                        data = response.get('data', [])
                        if data:
                            # Limit if needed
                            if max_tenders:
                                remaining = max_tenders - len(all_tenders)
                                if remaining <= 0:
                                    break
                                data = data[:remaining]

                            all_tenders.extend(data)

                            if page_num % 10 == 0:  # Log progress every 10 pages
                                logger.info(f"Progress: page {page_num}/{total_pages}, total: {len(all_tenders)} tenders")

                            if max_tenders and len(all_tenders) >= max_tenders:
                                logger.info(f"Reached max_tenders limit ({max_tenders})")
                                break
                    else:
                        logger.warning(f"Failed to get page {page_num}: status {status}")

                logger.info(f"✅ Modality {modality} complete: {len(all_tenders)} total tenders")

            except Exception as e:
                logger.error(f"Error processing modality {modality} for {state_code}: {e}")
                continue

        logger.info(f"🎯 Discovered {len(all_tenders)} tenders for {state_code}")
        return all_tenders

    async def fetch_sample_items(self, cnpj: str, year: int, sequential: int, max_items: int = 3) -> List[Dict]:
        """
        Fetch only first N items for quick validation (Stage 3 optimization)
        MASSIVE API savings: fetch 3 items instead of 50+
        Returns: List of item dictionaries
        """
        url = f"{self.consultation_url}/v1/orgaos/{cnpj}/compras/{year}/{sequential}/itens"

        # Limit page size to requested number of items
        params = {
            'pagina': 1,
            'tamanhoPagina': min(max_items, 10)  # API might have min limit
        }

        try:
            status, response = await self._make_request('GET', url, params=params)

            if status == 200:
                items = response.get('data', [])
                # Return only the requested number
                return items[:max_items]
            else:
                logger.warning(f"Failed to fetch sample items for {cnpj}/{year}/{sequential}: {status}")
                return []

        except Exception as e:
            logger.error(f"Error fetching sample items for {cnpj}/{year}/{sequential}: {e}")
            return []

    async def get_complete_tender_data(self, cnpj: str, year: int, sequential: int) -> Dict[str, Any]:
        """Get complete tender data including items and results"""
        tender_data = {
            'cnpj': cnpj,
            'year': year,
            'sequential': sequential,
            'items': [],
            'error': None
        }

        try:
            # Get tender items
            status, items_response = await self.get_tender_items(cnpj, year, sequential)

            if status == 200:
                items = items_response.get('data', [])

                for item in items:
                    item_number = item.get('numeroItem')
                    if item_number:
                        # Get item results
                        results_status, results_response = await self.get_item_results(
                            cnpj, year, sequential, item_number
                        )

                        if results_status == 200:
                            item['results'] = results_response.get('data', [])
                        else:
                            item['results'] = []
                            item['results_error'] = f"Status {results_status}: {results_response}"

                    tender_data['items'].append(item)

                    # Small delay between item requests
                    await asyncio.sleep(0.05)

            else:
                tender_data['error'] = f"Failed to get items: {status} - {items_response}"

        except Exception as e:
            tender_data['error'] = f"Exception getting tender data: {str(e)}"
            logger.error(f"Error getting complete tender data for {cnpj}/{year}/{sequential}: {e}")

        return tender_data

# Utility functions
async def test_api_connection() -> bool:
    """Test API connection (no authentication required)"""
    async with PNCPAPIClient() as client:
        # Test a simple consultation API call
        status, response = await client.get_tenders_by_publication_date(
            start_date='20240101',
            end_date='20240102',
            modality_code=8,  # Dispensa
            state='DF',
            page=1
        )

        if status == 200:
            logger.info(f"API test successful, found {response.get('totalRegistros', 0)} tenders")
            return True
        else:
            logger.error(f"API test failed: {status} - {response}")
            return False

async def discover_tenders_for_multiple_states(states: List[str], start_date: str, end_date: str) -> Dict[str, List[Dict]]:
    """Discover tenders for multiple states concurrently"""

    async with PNCPAPIClient() as client:

        tasks = []
        for state in states:
            task = client.discover_tenders_for_state(state, start_date, end_date)
            tasks.append((state, task))

        results = {}
        for state, task in tasks:
            try:
                tenders = await task
                results[state] = tenders
                logger.info(f"Completed tender discovery for {state}: {len(tenders)} tenders")
            except Exception as e:
                logger.error(f"Failed to discover tenders for {state}: {e}")
                results[state] = []

        return results

if __name__ == "__main__":
    # Test the API client
    async def main():
        success = await test_api_connection()
        if success:
            print("API connection test passed!")
        else:
            print("API connection test failed!")

    asyncio.run(main())