#!/usr/bin/env python3
"""
Step 2: AI-powered matching using Gemini 2.5 Flash
Matches filtered tender items to Fernandes product catalog
"""

import asyncio
import json
import os
import logging
import time
from datetime import datetime
from typing import List, Dict
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ai_matching.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class GeminiMatcher:
    """AI-powered product matcher using Gemini"""

    def __init__(self):
        # Configure Gemini API
        logger.info("🔧 Initializing Gemini Matcher...")
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in .env file")

        genai.configure(api_key=api_key)
        logger.info("✅ API key configured")

        # Use Gemini 2.5 Flash for speed and cost efficiency
        self.model = genai.GenerativeModel('gemini-2.5-flash')
        logger.info("✅ Model initialized: gemini-2.5-flash")

        self.fernandes_catalog = []
        self.batch_size = 50  # Items to process per API call
        logger.info(f"✅ Batch size set to: {self.batch_size}")

    def load_fernandes_catalog(self, filepath: str = 'config/fernandes_products.json'):
        """Load Fernandes product catalog"""
        logger.info(f"📂 Loading Fernandes catalog from {filepath}...")

        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Data is a list of products
            if isinstance(data, list):
                self.fernandes_catalog = data
            else:
                self.fernandes_catalog = data.get('products', [])

        logger.info(f"✅ Loaded {len(self.fernandes_catalog)} Fernandes products")

        # Log product names for verification
        for i, product in enumerate(self.fernandes_catalog[:3], 1):
            desc = product.get('DESCRIÇÃO') or product.get('name', '')
            logger.debug(f"   Product {i}: {desc[:50]}...")

    def create_catalog_text(self) -> str:
        """Create formatted catalog text for prompt"""
        catalog_lines = []
        for i, product in enumerate(self.fernandes_catalog, 1):
            desc = product.get('DESCRIÇÃO') or product.get('name', '')
            price = product.get('Price BRL') or product.get('price', 0)
            catalog_lines.append(
                f"{i}. {desc} - R$ {price:.2f}"
            )
        return "\n".join(catalog_lines)

    def create_matching_prompt(self, items_batch: List[Dict]) -> str:
        """Create AI matching prompt for a batch of items"""

        catalog_text = self.create_catalog_text()

        # Format tender items
        items_text = []
        for item in items_batch:
            items_text.append(
                f"[ID: {item['id']}] \"{item['description']}\" - "
                f"R$ {item['homologated_unit_value']:.2f} - "
                f"Qty: {item['quantity']} {item['unit']}"
            )
        items_str = "\n".join(items_text)

        prompt = f"""You are a medical product matching expert specialized in Brazilian healthcare procurement.

Your task is to match tender items to Fernandes Medical Products catalog.

**FERNANDES CATALOG:**
{catalog_text}

**TENDER ITEMS TO MATCH:**
{items_str}

**MATCHING INSTRUCTIONS:**
1. Match each tender item to the MOST SIMILAR Fernandes product BY DESCRIPTION ONLY
2. IGNORE product codes - focus ONLY on the description text
3. Consider:
   - Product type (curativo, film, gaze, etc.)
   - Dimensions and specifications
   - Material and characteristics (transparente, adesivo, etc.)
   - Intended use (IV, ferida, etc.)

4. Confidence levels:
   - 95-100%: Exact match (same product, dimensions, type)
   - 85-94%: Very close match (minor variations in description)
   - 75-84%: Good match (same category, similar specs)
   - 60-74%: Possible match (same category, different specs)
   - 50-59%: Weak match (same general category)
   - Below 50%: No reliable match

5. Only return matches with confidence ≥ 50%

6. If a tender item has NO good match, omit it from results

**OUTPUT FORMAT:**
Return ONLY a valid JSON array, no other text:

[
  {{
    "tender_item_id": 123,
    "tender_item_description": "Full tender item description here",
    "tender_item_price": 45.50,
    "fernandes_index": 5,
    "fernandes_description": "CURATIVO IV TRANSP. FENESTRADO COM BORDA - 7X9CM",
    "confidence": 95,
    "reasoning": "Exact match: transparent IV dressing, identical dimensions"
  }}
]

**IMPORTANT:**
- Use "fernandes_index" to reference the catalog number (1, 2, 3, etc.)
- Include "tender_item_description" with the full tender item description
- Include "tender_item_price" with the homologated unit value (the R$ price shown)
- Return ONLY the JSON array
- Do not include markdown code blocks
- Do not include explanatory text
- Ensure valid JSON syntax
"""

        return prompt

    async def match_batch(self, items_batch: List[Dict]) -> List[Dict]:
        """Match a batch of items using Gemini"""

        logger.info(f"🤖 Starting batch matching for {len(items_batch)} items")
        batch_start = time.time()

        prompt = self.create_matching_prompt(items_batch)
        prompt_length = len(prompt)
        logger.info(f"   Prompt created: {prompt_length} characters")

        try:
            # Generate content
            logger.info(f"   📡 Sending request to Gemini API...")
            api_start = time.time()
            response = self.model.generate_content(prompt)
            api_time = time.time() - api_start
            logger.info(f"   ✅ API responded in {api_time:.2f}s")

            # Extract text
            response_text = response.text.strip()
            logger.info(f"   Response size: {len(response_text)} characters")
            logger.debug(f"   Response preview: {response_text[:200]}...")

            # Clean up response (remove markdown code blocks if present)
            if response_text.startswith('```'):
                logger.info(f"   🧹 Cleaning markdown code blocks from response")
                lines = response_text.split('\n')
                response_text = '\n'.join(
                    line for line in lines
                    if not line.strip().startswith('```')
                )

            # Parse JSON
            logger.info(f"   🔍 Parsing JSON response...")
            matches = json.loads(response_text)

            batch_time = time.time() - batch_start
            logger.info(f"✅ Found {len(matches)} matches in {batch_time:.2f}s")

            return matches

        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON parsing error: {e}")
            logger.error(f"   Response text: {response_text[:500]}...")
            logger.error(f"   Full response saved to error log")
            with open('json_error_response.txt', 'w') as f:
                f.write(response_text)
            return []

        except Exception as e:
            logger.error(f"❌ API error: {type(e).__name__}: {e}")
            import traceback
            logger.error(f"   Traceback: {traceback.format_exc()}")
            return []

    async def match_all_items(self, items: List[Dict]) -> List[Dict]:
        """Match all items in batches"""

        all_matches = []
        total_batches = (len(items) + self.batch_size - 1) // self.batch_size

        logger.info(f"\n{'='*70}")
        logger.info(f"🚀 Starting AI matching...")
        logger.info(f"Total items: {len(items)}")
        logger.info(f"Batch size: {self.batch_size}")
        logger.info(f"Total batches: {total_batches}")
        logger.info(f"{'='*70}")

        overall_start = time.time()
        batch_times = []

        for i in range(0, len(items), self.batch_size):
            batch_num = i // self.batch_size + 1
            batch = items[i:i + self.batch_size]

            logger.info(f"\n{'='*70}")
            logger.info(f"📦 Processing batch {batch_num}/{total_batches}")
            logger.info(f"{'='*70}")

            batch_start = time.time()
            matches = await self.match_batch(batch)
            batch_elapsed = time.time() - batch_start
            batch_times.append(batch_elapsed)

            all_matches.extend(matches)

            # Calculate ETA
            avg_batch_time = sum(batch_times) / len(batch_times)
            remaining_batches = total_batches - batch_num
            eta_seconds = avg_batch_time * remaining_batches
            eta_minutes = eta_seconds / 60

            logger.info(f"📊 Progress: {batch_num}/{total_batches} batches ({(batch_num/total_batches)*100:.1f}%)")
            logger.info(f"⏱️  Batch time: {batch_elapsed:.2f}s | Avg: {avg_batch_time:.2f}s")
            logger.info(f"⏳ ETA: {eta_minutes:.1f} minutes ({eta_seconds:.0f}s)")
            logger.info(f"🎯 Total matches so far: {len(all_matches)}")

            # Small delay to respect rate limits
            if i + self.batch_size < len(items):
                await asyncio.sleep(0.5)

        total_time = time.time() - overall_start
        logger.info(f"\n🎉 All batches completed in {total_time:.2f}s ({total_time/60:.1f} minutes)")

        return all_matches

    def save_results(self, matches: List[Dict], output_file: str = 'data/ai_matches.json'):
        """Save matching results to file"""

        logger.info(f"\n💾 Saving results to {output_file}...")

        # Organize by confidence tiers (handle None values)
        high_confidence = [m for m in matches if m.get('confidence') is not None and m['confidence'] >= 90]
        medium_confidence = [m for m in matches if m.get('confidence') is not None and 70 <= m['confidence'] < 90]
        low_confidence = [m for m in matches if m.get('confidence') is not None and 50 <= m['confidence'] < 70]
        very_low_confidence = [m for m in matches if m.get('confidence') is not None and m['confidence'] < 50]
        no_confidence = [m for m in matches if m.get('confidence') is None]

        logger.info(f"   High confidence: {len(high_confidence)}")
        logger.info(f"   Medium confidence: {len(medium_confidence)}")
        logger.info(f"   Low confidence: {len(low_confidence)}")
        logger.info(f"   Very low confidence: {len(very_low_confidence)}")
        logger.info(f"   No confidence: {len(no_confidence)}")

        results = {
            'matched_at': datetime.now().isoformat(),
            'total_matches': len(matches),
            'high_confidence': len(high_confidence),
            'medium_confidence': len(medium_confidence),
            'low_confidence': len(low_confidence),
            'very_low_confidence': len(very_low_confidence),
            'no_confidence': len(no_confidence),
            'matches': matches,
            'tiers': {
                'high_confidence': high_confidence,
                'medium_confidence': medium_confidence,
                'low_confidence': low_confidence,
                'very_low_confidence': very_low_confidence,
                'no_confidence': no_confidence
            }
        }

        os.makedirs('data', exist_ok=True)

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        logger.info(f"✅ Saved {len(matches)} matches to {output_file}")

        # Print statistics
        logger.info("\n" + "=" * 70)
        logger.info("📊 MATCHING STATISTICS")
        logger.info("=" * 70)
        logger.info(f"Total Matches: {len(matches):,}")
        logger.info(f"High Confidence (≥90%): {len(high_confidence):,}")
        logger.info(f"Medium Confidence (70-89%): {len(medium_confidence):,}")
        logger.info(f"Low Confidence (50-69%): {len(low_confidence):,}")
        logger.info(f"Very Low Confidence (<50%): {len(very_low_confidence):,}")
        logger.info(f"No Confidence: {len(no_confidence):,}")

        if matches:
            matches_with_confidence = [m for m in matches if m.get('confidence') is not None]
            if matches_with_confidence:
                avg_confidence = sum(m['confidence'] for m in matches_with_confidence) / len(matches_with_confidence)
                logger.info(f"Average Confidence: {avg_confidence:.1f}%")

        return results


async def main():
    """Main matching workflow"""

    logger.info("=" * 70)
    logger.info("🤖 AI-POWERED PRODUCT MATCHING - GEMINI 2.5 FLASH")
    logger.info("=" * 70)

    # Load filtered items
    items_file = 'data/filtered_items_for_matching.json'

    logger.info(f"\n📂 Loading filtered items from {items_file}...")

    if not os.path.exists(items_file):
        logger.error(f"❌ Error: {items_file} not found!")
        logger.error("   Run ai_matching_step1_extract.py first")
        return

    with open(items_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
        items = data['items']

    logger.info(f"✅ Loaded {len(items)} items")
    logger.info(f"   First item: {items[0]['description'][:60]}..." if items else "   No items found")

    # Initialize matcher
    matcher = GeminiMatcher()

    # Load Fernandes catalog
    matcher.load_fernandes_catalog()

    # Match items
    logger.info(f"\n🚀 Starting matching process...")
    matches = await matcher.match_all_items(items)

    # Save results
    matcher.save_results(matches)

    logger.info("\n" + "=" * 70)
    logger.info("✅ MATCHING COMPLETE")
    logger.info("=" * 70)
    logger.info("\n📁 Next step: Run ai_matching_step3_save.py to save to database")
    logger.info(f"📝 Full log saved to: ai_matching.log")


if __name__ == "__main__":
    asyncio.run(main())
