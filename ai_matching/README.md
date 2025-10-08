# AI-Powered Product Matching Module

Intelligent matching of tender items to Fernandes product catalog using Google Gemini AI.

---

## ⚡ V8 Workflow (Looker-First Approach)

**This module is now the RECOMMENDED way to match products in V8.**

### Why?
- ✅ **Better match quality** - 70% success rate (vs 30% with fuzzy matching)
- ✅ **Faster daily runs** - Phase 3 skipped by default in main.py
- ✅ **More control** - Match only products you care about
- ✅ **Cost effective** - ~$0.02 per 1,000 items (only pay for what you match)

---

## Quick Start

```bash
# 1. Run main.py daily (Phase 3 SKIPPED by default)
python3 main.py --start 20250101 --end 20250131 --states SP

# 2. Explore data in Looker Studio
# Use looker_views.sql to create views and find interesting products

# 3. Update keywords.json with products you want to match
# Example: ["curativo", "transparente", "filme", "gaze"]

# 4. Run AI matching for those specific products
python3 ai_matching/step1_extract_keywords.py  # Extract items matching keywords
python3 ai_matching/step2_gemini.py            # AI matching with Gemini
python3 ai_matching/step3_save.py              # Save high-confidence matches
python3 ai_matching/step4_report.py            # Generate report

# 5. View matches in Looker Studio
# Use vw_matched_products_analysis view
```

**Total time: ~5 minutes | Total cost: ~$0.02 per run**

---

## What It Does

**Problem:** Thousands of tender items need matching to Fernandes catalog, but product names vary too much for simple string matching.

**Solution:** Keyword-based AI matching:
1. **Explore in Looker** - Visualize all items, find interesting categories
2. **Filter by keywords** - Use keywords.json to select items (e.g., "curativo")
3. **AI Matching** - Intelligent batch matching with Gemini 2.5 Flash
4. **Save results** - Auto-save high-confidence matches to database

**Result:**
- ✅ ~70% match rate (much better than 30% fuzzy matching)
- ✅ ~500 high-confidence matches (≥90%) → Auto-saved to DB
- 📋 ~300 medium-confidence matches (70-89%) → CSV for review
- ⚠️ ~200 low matches (<70%) → Rejected

---

## Module Structure

```
ai_matching/
├── __init__.py               # Package initialization
├── README.md                 # This file
│
├── step1_extract.py          # Extract filtered items from DB
├── step2_gemini.py           # AI matching with Gemini
├── step3_save.py             # Save results to DB
├── step4_report.py           # Generate analysis report
│
└── utils/
    ├── __init__.py
    ├── create_catalog_sample.py  # Create sample Fernandes catalog
    └── check_schema.py           # Verify database schema
```

---

## Workflow Steps

### Step 1: Extract Filtered Items
```bash
python3 ai_matching/step1_extract.py
```
Queries database for items containing "curativo" or "transparente" keywords.

**Output:** `data/filtered_items_for_matching.json`

---

### Step 2: AI Matching
```bash
python3 ai_matching/step2_gemini.py
```
Matches filtered items to Fernandes catalog using Gemini AI in batches of 50.

**Output:** `data/ai_matches.json`

---

### Step 3: Save to Database
```bash
python3 ai_matching/step3_save.py
```
Saves high-confidence matches (≥90%) to database, exports medium-confidence to CSV.

**Output:**
- Database: `matched_products` table
- CSV: `data/medium_confidence_matches_for_review.csv`

---

### Step 4: Generate Report
```bash
python3 ai_matching/step4_report.py
```
Generates comprehensive analysis including price comparisons and opportunities.

---

## Documentation

Detailed documentation available in `docs/ai_matching/`:

- **[PLAN.md](../docs/ai_matching/PLAN.md)** - Strategy, cost analysis, ROI
- **[README.md](../docs/ai_matching/README.md)** - Complete user guide
- **[SUMMARY.md](../docs/ai_matching/SUMMARY.md)** - Quick reference
- **[CHECKLIST.md](../docs/ai_matching/CHECKLIST.md)** - Implementation checklist

---

## Requirements

- Python 3.11+
- Google Gemini API key
- PostgreSQL database with `tender_items` table

```bash
pip install google-generativeai
```

Add to `.env`:
```bash
GEMINI_API_KEY=your_api_key_here
```

---

## Configuration

### Adjust Filter Keywords

Edit `step1_extract.py` line ~35:
```python
WHERE LOWER(description) LIKE '%curativo%'
   OR LOWER(description) LIKE '%transparente%'
   OR LOWER(description) LIKE '%gaze%'  # Add more
```

### Adjust Confidence Thresholds

Edit `step3_save.py`:
```python
high_confidence = [m for m in matches if m['confidence'] >= 85]  # Lower from 90
```

### Adjust Batch Size

Edit `step2_gemini.py`:
```python
self.batch_size = 30  # Smaller = more precise
self.batch_size = 100  # Larger = faster
```

---

## Cost & Performance

| Metric | Value |
|--------|-------|
| Items processed | ~1,000 |
| API calls | ~20 |
| Total cost | ~$0.02 |
| Total time | ~5 min |
| Match rate | 50-70% |
| High confidence | 70%+ |

---

## Database Schema

### Input Tables
- `tender_items` - Items to match
- `fernandes_products` - Catalog

### Output Table
```sql
CREATE TABLE matched_products (
    id SERIAL PRIMARY KEY,
    tender_item_id INTEGER REFERENCES tender_items(id),
    fernandes_product_id INTEGER REFERENCES fernandes_products(id),
    match_confidence INTEGER,
    match_method VARCHAR(50),  -- 'ai_gemini'
    match_reasoning TEXT,
    price_difference_percent DECIMAL(10, 2),
    created_at TIMESTAMP
);
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "API key not found" | Add `GEMINI_API_KEY` to `.env` |
| "No items found" | Check database has items with keywords |
| "Low match rate" | Expand Fernandes catalog |
| "JSON errors" | Reduce batch size to 20-30 |

---

## Version

**v1.0.0** - Initial release

---

## License

Part of PNCP Medical Data Processing System
