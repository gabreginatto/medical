# Session Notes - October 2, 2025

## Summary
Today we worked on verifying that tender items with homologated prices are properly saved in the database, discovered and fixed an API issue, and prepared for the product matching phase. We hit a database permissions issue at the end that needs to be resolved tomorrow.

---

## 1. What We Accomplished Today

### ✅ Verified Homologated Price Extraction
- **Issue Found**: Initially, 584 items were in the database but 0 had homologated prices
- **Root Cause**: The PNCP API's `/itens` endpoint doesn't include homologated prices - they're in a separate `/resultados` endpoint
- **Solution**: Updated `fetch_and_save_items.py` to make a second API call to `/resultados` for each item that has `temResultado: true`

### ✅ Successfully Fetched Homologated Prices
- **Result**: 465 out of 584 items (79.6%) now have homologated prices
- **Verification**: Checked tender `60448040000122-1-000196/2024` in the PNCP portal and confirmed prices match
- **Note**: 119 items without homologated prices are from partially awarded tenders (normal behavior)

### ✅ Extracted Fernandes Product Catalog
- **Created**: `extract_fernandes_products.py` to parse PDF and extract product data
- **Result**: Successfully extracted 16 Fernandes products from `Docs/Fernandes-price-20250805 (1).pdf`
- **Output Files**:
  - `fernandes_products.json` - 16 products with codes, descriptions, FOB prices (USD), and MOQ
  - `fernandes_products.csv` - Same data in CSV format

### ✅ Prepared Product Matching Infrastructure
- **Created**: `match_tender_items.py` - orchestration script to match tender items against Fernandes catalog
- **Added**: `insert_matched_product()` method to `database.py` for saving matches
- **Purpose**: Match 465 tender items (with homologated prices) against 16 Fernandes products

---

## 2. Scripts Created/Modified Today

### New Scripts

1. **`extract_fernandes_products.py`**
   - Purpose: Extract Fernandes product catalog from PDF
   - Uses PyPDF2 and regex to parse product data
   - Outputs to JSON and CSV formats

2. **`match_tender_items.py`**
   - Purpose: Orchestrate product matching workflow
   - Loads Fernandes products from JSON
   - Fetches tender items with homologated prices from database
   - Uses `ProductMatcher` class to find best matches
   - Calculates price comparisons (homologated vs FOB)
   - Saves matches to `matched_products` table

3. **`add_is_competitive_column.py`**
   - Purpose: Add missing `is_competitive` column to database
   - Currently blocked by permissions issue
   - Needs to be run with postgres admin privileges

### Modified Scripts

1. **`fetch_and_save_items.py`** (lines 135-151)
   - Added logic to fetch homologated prices from `/resultados` endpoint
   - Checks if item has `temResultado: true`
   - Calls `get_item_results()` API for those items
   - Extracts homologated prices and winner information

2. **`database.py`** (lines 503-528)
   - Added `insert_matched_product()` method to DatabaseOperations class
   - Handles INSERT with ON CONFLICT for deduplication
   - Updates existing matches if run multiple times

---

## 3. The Current Test We're Attempting

### Goal
Match our 465 tender items (with homologated prices) against the 16 Fernandes products to identify competitive opportunities.

### What It Does
```
For each tender item:
  1. Use ProductMatcher to find best match in Fernandes catalog (min 50% similarity)
  2. If match found:
     - Calculate FOB price in BRL (using USD exchange rate)
     - Compare homologated price vs FOB price
     - Calculate savings percentage
     - Determine if competitive (>10% savings)
  3. Save match to matched_products table
```

### Example Output
```
Tender Item: CURATIVO TRANSPARENTE FENESTRADO 5X7CM
Fernandes Product: IVFS.5057 - CURATIVO IV TRANSP. FENESTRADO
Match Score: 87.3%
Market Price: R$ 0.45
Our FOB Price: R$ 0.37 ($0.074)
Savings: 21.6%
Competitive: ✅ Yes
```

### Current Blocker
The script failed with: `column "is_competitive" does not exist`

---

## 4. Database Schema Issue

### The Missing Column: `is_competitive`

**Purpose**:
This boolean column indicates whether a matched product represents a competitive business opportunity. It's automatically calculated based on the price difference between:
- **Homologated Price** (what the government actually paid)
- **FOB Price** (what Fernandes can offer)

**Logic**:
```python
is_competitive = price_difference_percent > 10
# True if Fernandes FOB price is at least 10% cheaper than market price
```

**Why It Matters**:
This column allows us to quickly query and export only the truly competitive opportunities to Notion, filtering out products where Fernandes can't compete on price.

### What Needs to Be Done Tomorrow

The `matched_products` table schema in `database.py` line 199 includes `is_competitive BOOLEAN`, but the actual database table doesn't have this column yet.

**Solution Options**:

1. **Option A (Simple)**: Connect to Cloud SQL and run:
   ```sql
   ALTER TABLE matched_products ADD COLUMN is_competitive BOOLEAN;
   ```

2. **Option B (Proper)**: Re-run the database schema initialization to ensure all tables match the code definition.

**Current Issue**:
- Script `add_is_competitive_column.py` has permission error: "must be owner of table matched_products"
- The service account user doesn't have ALTER TABLE privileges
- Need to use postgres admin user or grant privileges

---

## 5. Tomorrow's Plan: Organizing Everything

### Current State of the Project

We have **standalone scripts** that work individually:
- ✅ `tender_discovery.py` - Discovers tenders
- ✅ `fetch_and_save_items.py` - Extracts items and homologated prices
- ⏳ `match_tender_items.py` - Matches products (ready, blocked by DB column)
- ⏭️ `notion_integration.py` - Exports to Notion (not tested yet)

### The Problem

The README says users should run:
```bash
python main.py --start-date 20240101 --end-date 20240131 --states SP RJ
```

But `main.py` doesn't exist! We found a legacy version in `backup/v1_legacy/main.py` but it's outdated.

### Tomorrow's Tasks

#### Task 1: Fix the Database Column Issue
1. Add the `is_competitive` column to the database
2. Options:
   - Use postgres admin credentials to run ALTER TABLE
   - Or grant the service account ALTER TABLE privilege
   - Or re-initialize the entire schema

#### Task 2: Test Product Matching
1. Once column is added, run `match_tender_items.py`
2. Verify it successfully matches items
3. Check the results in the database:
   ```sql
   SELECT COUNT(*) FROM matched_products WHERE is_competitive = true;
   ```

#### Task 3: Create the Main Orchestration Script

Based on the legacy `main.py` and current scripts, we need to create a new `main.py` that:

**Architecture**:
```python
class PNCPMedicalProcessor:
    def __init__(self, config):
        # Initialize all components

    async def run_complete_workflow(self, start_date, end_date, states):
        # Phase 1: Tender Discovery
        await self.discover_tenders()

        # Phase 2: Item Extraction (with homologated prices)
        await self.fetch_and_save_items()

        # Phase 3: Product Matching
        await self.match_tender_items()

        # Phase 4: Export to Notion
        await self.export_to_notion()
```

**Command Line Interface**:
```bash
# Full workflow
python main.py --start-date 20240101 --end-date 20240131 --states SP RJ

# Discovery only
python main.py --start-date 20240101 --end-date 20240131 --discovery-only

# Item processing only (for existing tenders)
python main.py --items-only

# Product matching only (for existing items)
python main.py --matching-only

# Notion export only
python main.py --export-only
```

**What to Reuse**:
- From legacy `main.py`: CLI argument parsing, workflow orchestration structure
- From current scripts: The actual implementation logic (tender_discovery, fetch_and_save_items, match_tender_items)

**What to Change**:
- Update API calls to match current implementation
- Remove references to obsolete `item_processor.py` (we use `fetch_and_save_items.py` now)
- Update to use current database schema
- Integrate the homologated price fetching logic

#### Task 4: Test the Complete Workflow

Once `main.py` is created, test it end-to-end:

```bash
# Small test with just DF state, last 7 days
python main.py --start-date 20241001 --end-date 20241007 --states DF
```

Expected flow:
1. Discover tenders for DF from Oct 1-7
2. Save new tenders to database
3. Fetch items and homologated prices
4. Match items against Fernandes catalog
5. Export competitive opportunities to Notion

---

## 6. Data Summary

### Current Database State
- **Organizations**: Multiple government entities
- **Tenders**: 132 tenders discovered
- **Tender Items**: 584 items
  - With homologated prices: 465 (79.6%)
  - Without homologated prices: 119 (20.4%, partially awarded tenders)
- **Matched Products**: 0 (blocked by missing column)

### Fernandes Catalog
- **Total Products**: 16
- **Categories**: Medical dressings and wound care
- **Price Range**: $0.0418 - $0.2033 USD per unit
- **MOQ Range**: 40,000 - 100,000 units

---

## 7. Files Modified/Created Summary

### Created Files
```
extract_fernandes_products.py     - PDF extraction script
match_tender_items.py             - Product matching orchestration
add_is_competitive_column.py      - DB schema fix script
fernandes_products.json           - Extracted product data (16 products)
fernandes_products.csv            - Same data in CSV format
SESSION_NOTES.md                  - This file
```

### Modified Files
```
fetch_and_save_items.py           - Added homologated price fetching (lines 135-151)
database.py                       - Added insert_matched_product() method (lines 503-528)
```

---

## 8. Technical Notes

### API Structure
- **Tender List**: `/pncp-api/consulta/v1/contratacoes/publicacao`
- **Tender Items**: `/pncp-api/consulta/v1/contratacoes/{ano}/{sequencial}/itens`
- **Item Results**: `/pncp-api/consulta/v1/contratacoes/{ano}/{sequencial}/itens/{itemNumero}/resultados`

### Key Insight
The PNCP API requires TWO separate calls per tender:
1. First call to `/itens` gets item metadata
2. Second call to `/resultados` per item gets the actual homologated prices

### Exchange Rate
Currently hardcoded to 5.0 BRL/USD in `match_tender_items.py` (line 68). Should be made configurable or fetched from an API.

---

## 9. Open Questions for Tomorrow

1. **Database Permissions**: How should we handle schema changes? Service account vs postgres admin?
2. **Exchange Rate**: Should we fetch real-time USD/BRL rates or use a configurable value?
3. **Match Threshold**: Is 50% similarity score appropriate or should we adjust it?
4. **Competitive Threshold**: Is 10% savings the right threshold for "competitive"?
5. **Notion Integration**: What should the Notion database schema look like?

---

## 10. Commands to Remember

```bash
# Check items with homologated prices
python3 show_sample_items.py

# Extract products from PDF (already done)
python3 extract_fernandes_products.py

# Run product matching (blocked by DB column)
python3 match_tender_items.py

# Add missing column (blocked by permissions)
python3 add_is_competitive_column.py
```

---

**Session End**: Database column issue needs to be resolved before product matching can proceed. Main orchestration script (`main.py`) needs to be created to unify all standalone scripts into a cohesive workflow as described in the README.
