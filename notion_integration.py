"""
Notion API Integration for PNCP Medical Data
Pushes tender results directly to Notion databases
"""

import os
import json
import asyncio
import aiohttp
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class NotionConfig:
    """Notion integration configuration"""
    API_TOKEN: str = os.getenv('NOTION_API_TOKEN', '')
    TENDERS_DATABASE_ID: str = os.getenv('NOTION_TENDERS_DB_ID', '')
    ITEMS_DATABASE_ID: str = os.getenv('NOTION_ITEMS_DB_ID', '')
    OPPORTUNITIES_DATABASE_ID: str = os.getenv('NOTION_OPPORTUNITIES_DB_ID', '')
    BASE_URL: str = "https://api.notion.com/v1"
    API_VERSION: str = "2022-06-28"

class NotionClient:
    """Notion API client for PNCP data integration"""

    def __init__(self, config: NotionConfig = None):
        self.config = config or NotionConfig()
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            headers={
                "Authorization": f"Bearer {self.config.API_TOKEN}",
                "Notion-Version": self.config.API_VERSION,
                "Content-Type": "application/json"
            }
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def create_page(self, database_id: str, properties: Dict[str, Any]) -> Dict:
        """Create a new page in a Notion database"""
        url = f"{self.config.BASE_URL}/pages"
        data = {
            "parent": {"database_id": database_id},
            "properties": properties
        }

        async with self.session.post(url, json=data) as response:
            if response.status == 200:
                return await response.json()
            else:
                error_text = await response.text()
                logger.error(f"Notion API error: {response.status} - {error_text}")
                raise Exception(f"Notion API error: {response.status}")

    async def query_database(self, database_id: str, filter_data: Dict = None) -> List[Dict]:
        """Query a Notion database"""
        url = f"{self.config.BASE_URL}/databases/{database_id}/query"
        data = {"filter": filter_data} if filter_data else {}

        async with self.session.post(url, json=data) as response:
            if response.status == 200:
                result = await response.json()
                return result.get('results', [])
            else:
                logger.error(f"Query error: {response.status}")
                return []

    async def update_page(self, page_id: str, properties: Dict[str, Any]) -> Dict:
        """Update an existing page"""
        url = f"{self.config.BASE_URL}/pages/{page_id}"
        data = {"properties": properties}

        async with self.session.patch(url, json=data) as response:
            if response.status == 200:
                return await response.json()
            else:
                logger.error(f"Update error: {response.status}")
                raise Exception(f"Update failed: {response.status}")

class NotionDataExporter:
    """Export PNCP data to Notion databases"""

    def __init__(self, notion_client: NotionClient):
        self.notion = notion_client

    def format_tender_properties(self, tender_data: Dict) -> Dict[str, Any]:
        """Format tender data for Notion database"""
        return {
            "Title": {
                "title": [{"text": {"content": tender_data.get('title', 'Untitled Tender')[:100]}}]
            },
            "Organization": {
                "rich_text": [{"text": {"content": tender_data.get('organization_name', '')[:2000]}}]
            },
            "CNPJ": {
                "rich_text": [{"text": {"content": tender_data.get('cnpj', '')}}]
            },
            "State": {
                "select": {"name": tender_data.get('state_code', 'N/A')}
            },
            "Government Level": {
                "select": {"name": tender_data.get('government_level', 'Unknown')}
            },
            "Total Value (R$)": {
                "number": float(tender_data.get('total_homologated_value', 0))
            },
            "Publication Date": {
                "date": {"start": tender_data.get('publication_date', datetime.now().isoformat()[:10])}
            },
            "Status": {
                "select": {"name": "Homologated"}
            },
            "Items Count": {
                "number": tender_data.get('items_count', 0)
            },
            "Matches Found": {
                "number": tender_data.get('matches_count', 0)
            },
            "Processed Date": {
                "date": {"start": datetime.now().isoformat()[:10]}
            }
        }

    def format_item_properties(self, item_data: Dict) -> Dict[str, Any]:
        """Format item data for Notion database"""
        return {
            "Description": {
                "title": [{"text": {"content": item_data.get('description', 'No description')[:100]}}]
            },
            "Tender ID": {
                "rich_text": [{"text": {"content": str(item_data.get('tender_id', ''))}}]
            },
            "Organization": {
                "rich_text": [{"text": {"content": item_data.get('organization_name', '')[:100]}}]
            },
            "Item Number": {
                "number": item_data.get('item_number', 0)
            },
            "Unit": {
                "rich_text": [{"text": {"content": item_data.get('unit', '')}}]
            },
            "Quantity": {
                "number": float(item_data.get('quantity', 0))
            },
            "Unit Price (R$)": {
                "number": float(item_data.get('homologated_unit_value', 0))
            },
            "Total Price (R$)": {
                "number": float(item_data.get('homologated_total_value', 0))
            },
            "Winner": {
                "rich_text": [{"text": {"content": item_data.get('winner_name', '')[:100]}}]
            },
            "State": {
                "select": {"name": item_data.get('state_code', 'N/A')}
            },
            "Has Match": {
                "checkbox": bool(item_data.get('has_match', False))
            }
        }

    def format_opportunity_properties(self, opportunity_data: Dict) -> Dict[str, Any]:
        """Format competitive opportunity data for Notion database"""
        return {
            "Product": {
                "title": [{"text": {"content": opportunity_data.get('fernandes_product_description', 'Unknown Product')[:100]}}]
            },
            "Fernandes Code": {
                "rich_text": [{"text": {"content": opportunity_data.get('fernandes_product_code', '')}}]
            },
            "Tender Description": {
                "rich_text": [{"text": {"content": opportunity_data.get('tender_item_description', '')[:500]}}]
            },
            "Organization": {
                "rich_text": [{"text": {"content": opportunity_data.get('organization_name', '')[:100]}}]
            },
            "Match Score": {
                "number": float(opportunity_data.get('match_score', 0))
            },
            "FOB Price (USD)": {
                "number": float(opportunity_data.get('fob_price_usd', 0))
            },
            "Market Price (R$)": {
                "number": float(opportunity_data.get('price_comparison_brl', 0))
            },
            "Our Price (R$)": {
                "number": float(opportunity_data.get('fob_price_usd', 0) * opportunity_data.get('exchange_rate', 5.0))
            },
            "Price Difference (%)": {
                "number": float(opportunity_data.get('price_difference_percent', 0))
            },
            "Competitive": {
                "checkbox": bool(opportunity_data.get('is_competitive', False))
            },
            "State": {
                "select": {"name": opportunity_data.get('state_code', 'N/A')}
            },
            "Opportunity Score": {
                "select": {
                    "name": self._get_opportunity_score(opportunity_data.get('price_difference_percent', 0))
                }
            },
            "Quantity": {
                "number": float(opportunity_data.get('quantity', 0))
            },
            "Potential Revenue (R$)": {
                "number": float(opportunity_data.get('quantity', 0) * opportunity_data.get('fob_price_usd', 0) * opportunity_data.get('exchange_rate', 5.0))
            }
        }

    def _get_opportunity_score(self, price_diff: float) -> str:
        """Convert price difference to opportunity score"""
        if price_diff >= 50:
            return "🟢 High"
        elif price_diff >= 25:
            return "🟡 Medium"
        elif price_diff >= 10:
            return "🟠 Low"
        else:
            return "🔴 Poor"

    async def export_tenders(self, tenders: List[Dict]) -> int:
        """Export tenders to Notion database"""
        if not self.notion.config.TENDERS_DATABASE_ID:
            logger.warning("Tenders database ID not configured")
            return 0

        exported = 0
        for tender in tenders:
            try:
                properties = self.format_tender_properties(tender)
                await self.notion.create_page(
                    self.notion.config.TENDERS_DATABASE_ID,
                    properties
                )
                exported += 1
                logger.info(f"Exported tender: {tender.get('title', 'Unknown')[:50]}")

                # Rate limiting - Notion API allows 3 requests per second
                await asyncio.sleep(0.4)

            except Exception as e:
                logger.error(f"Failed to export tender {tender.get('id', 'unknown')}: {e}")

        return exported

    async def export_items(self, items: List[Dict]) -> int:
        """Export items to Notion database"""
        if not self.notion.config.ITEMS_DATABASE_ID:
            logger.warning("Items database ID not configured")
            return 0

        exported = 0
        for item in items:
            try:
                properties = self.format_item_properties(item)
                await self.notion.create_page(
                    self.notion.config.ITEMS_DATABASE_ID,
                    properties
                )
                exported += 1

                if exported % 10 == 0:
                    logger.info(f"Exported {exported} items...")

                await asyncio.sleep(0.4)

            except Exception as e:
                logger.error(f"Failed to export item {item.get('id', 'unknown')}: {e}")

        return exported

    async def export_opportunities(self, opportunities: List[Dict]) -> int:
        """Export competitive opportunities to Notion database"""
        if not self.notion.config.OPPORTUNITIES_DATABASE_ID:
            logger.warning("Opportunities database ID not configured")
            return 0

        # Filter for competitive opportunities only
        competitive_ops = [op for op in opportunities if op.get('is_competitive', False)]

        exported = 0
        for opp in competitive_ops:
            try:
                properties = self.format_opportunity_properties(opp)
                await self.notion.create_page(
                    self.notion.config.OPPORTUNITIES_DATABASE_ID,
                    properties
                )
                exported += 1
                logger.info(f"Exported opportunity: {opp.get('fernandes_product_code', 'Unknown')}")

                await asyncio.sleep(0.4)

            except Exception as e:
                logger.error(f"Failed to export opportunity {opp.get('id', 'unknown')}: {e}")

        return exported

async def export_to_notion(tenders: List[Dict], items: List[Dict], opportunities: List[Dict]):
    """Main function to export all data to Notion"""
    config = NotionConfig()

    # Validate configuration
    if not config.API_TOKEN:
        logger.error("NOTION_API_TOKEN not configured")
        return

    async with NotionClient(config) as notion:
        exporter = NotionDataExporter(notion)

        print("🔗 Exporting to Notion...")

        # Export tenders
        if config.TENDERS_DATABASE_ID and tenders:
            tender_count = await exporter.export_tenders(tenders)
            print(f"✅ Exported {tender_count} tenders")

        # Export items
        if config.ITEMS_DATABASE_ID and items:
            item_count = await exporter.export_items(items)
            print(f"✅ Exported {item_count} items")

        # Export opportunities
        if config.OPPORTUNITIES_DATABASE_ID and opportunities:
            opp_count = await exporter.export_opportunities(opportunities)
            print(f"✅ Exported {opp_count} competitive opportunities")

        print("🎉 Notion export complete!")

# Example usage and testing
async def test_notion_connection():
    """Test Notion API connection"""
    config = NotionConfig()

    if not config.API_TOKEN:
        print("❌ NOTION_API_TOKEN not configured")
        return False

    try:
        async with NotionClient(config) as notion:
            # Test with a simple database query
            if config.TENDERS_DATABASE_ID:
                results = await notion.query_database(config.TENDERS_DATABASE_ID)
                print(f"✅ Connection successful! Found {len(results)} existing records")
                return True
            else:
                print("⚠️  No database IDs configured, but API token works")
                return True

    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(test_notion_connection())