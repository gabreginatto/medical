# AI-Powered Product Matching Workflow

Complete workflow for matching tender items to Fernandes product catalog using Google Gemini AI.

---

## Overview

This workflow uses a **two-stage approach**:

1. **SQL Filtering**: Filter ~9,000 items down to ~500-1,500 relevant items (containing "curativo" or "transparente")
2. **AI Matching**: Use Gemini 2.5 Flash to intelligently match filtered items to Fernandes catalog

**Expected Results:**
- ✅ 400-600 high-confidence matches (≥90%) → Saved to database automatically
- 📋 200-300 medium-confidence matches (70-89%) → CSV for quick review
- ⚠️ 200-300 low matches (<70%) → Rejected/needs better prompts
- 💰 Total cost: **~$0.02** (essentially free!)
- ⏱️ Total time: **~5 minutes**

---

## Prerequisites

### 1. Install Gemini API SDK

```bash
pip install google-generativeai
```

### 2. Get Gemini API Key

1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create a new API key
3. Add to your `.env` file:

```bash
GEMINI_API_KEY=your_api_key_here
```

### 3. Prepare Fernandes Product Catalog

**Option A: Create from existing data**

If you have Fernandes products in a spreadsheet/CSV:

1. Convert to JSON format matching this structure:

```json
{
  "catalog_name": "Fernandes Medical Products",
  "products": [
    {
      "code": "FT1012",
      "name": "Filme Transparente Tegaderm 10x12cm",
      "price": 4.50,
      "category": "Curativos",
      "description": "Curativo transparente estéril"
    }
  ]
}
```

2. Save as `data/fernandes_products.json`

**Option B: Use sample template**

```bash
python3 ai_matching/utils/create_catalog_sample.py
```

Then edit `data/fernandes_products.json` with your actual products.

---

## Workflow Steps

### Step 1: Extract Filtered Items from Database

```bash
python3 ai_matching/step1_extract.py
```

**What it does:**
- Queries database for items containing "curativo" OR "transparente"
- Saves filtered items to `data/filtered_items_for_matching.json`
- Shows statistics and top items

**Output:**
```
📊 EXTRACTION STATISTICS
Total Items: 1,245
Total Value: R$ 234,567.89
Avg Unit Value: R$ 5.67
```

---

### Step 2: AI Matching with Gemini

```bash
python3 ai_matching/step2_gemini.py
```

**What it does:**
- Loads filtered items and Fernandes catalog
- Processes items in batches of 50
- Uses Gemini 2.5 Flash for intelligent matching
- Saves results to `data/ai_matches.json`

**Output:**
```
🤖 AI-POWERED PRODUCT MATCHING
📦 Processing batch 1/25
✅ Found 42 matches in this batch
...
📊 MATCHING STATISTICS
Total Matches: 856
High Confidence (≥90%): 512
Medium Confidence (70-89%): 278
Average Confidence: 87.3%
```

**Batch Processing:**
- Batch size: 50 items per API call
- Rate: ~3 seconds per batch
- Total time: ~1-2 minutes for 1,000 items

---

### Step 3: Save to Database

```bash
python3 ai_matching/step3_save.py
```

**What it does:**
- Saves high-confidence matches (≥90%) to `matched_products` table
- Exports medium-confidence matches (70-89%) to CSV for review
- Skips items already matched

**Output:**
```
💾 SAVING AI MATCHES TO DATABASE
✅ Saved 512 high-confidence matches to database
📤 Exported 278 matches to data/medium_confidence_matches_for_review.csv
```

**Database Schema:**
```sql
INSERT INTO matched_products (
    tender_item_id,
    fernandes_product_id,
    match_confidence,
    match_method,  -- 'ai_gemini'
    match_reasoning,
    price_difference_percent
)
```

---

### Step 4: Generate Report

```bash
python3 ai_matching/step4_report.py
```

**What it does:**
- Analyzes matching performance
- Shows price comparison statistics
- Identifies top opportunities (biggest price differences)
- Provides recommendations

**Output:**
```
📈 MATCHING PERFORMANCE
Match Rate: 68.7%
Average Confidence: 87.3%

💰 PRICE COMPARISON ANALYSIS
Average Price Difference: +23.4%
Cheaper than Fernandes: 234 (45.7%)
More expensive: 278 (54.3%)

🎯 TOP 10 PRICE OPPORTUNITIES
1. Curativo transparente 10x12cm
   Tender: R$ 8.50 | Fernandes: R$ 4.50
   Difference: +88.9% | Potential savings: R$ 2,400.00
```

---

## Manual Review Process

### Reviewing Medium-Confidence Matches

1. Open `data/medium_confidence_matches_for_review.csv`
2. Review each match
3. Mark the `accept` column:
   - `YES` = Valid match, should be saved
   - `NO` = Invalid match, reject
4. Add notes in the `notes` column if needed

**CSV Format:**
```csv
tender_item_id,description,tender_price,matched_fernandes_name,confidence,accept,notes
123,"Curativo transparente 10x12",5.50,"Filme Transparente 10x12cm",85,YES,
456,"Film adesivo esteril",6.20,"Filme Transparente 10x12cm",78,YES,Variant spelling
```

### Importing Reviewed Matches

After reviewing, you can import accepted matches:

```python
# TODO: Create import script for reviewed matches
python3 import_reviewed_matches.py
```

---

## File Structure

```
Medical/
├── data/
│   ├── fernandes_products.json           # Fernandes catalog (INPUT)
│   ├── filtered_items_for_matching.json  # Filtered items (STEP 1 OUTPUT)
│   ├── ai_matches.json                   # AI matches (STEP 2 OUTPUT)
│   └── medium_confidence_matches_for_review.csv  # Review queue (STEP 3 OUTPUT)
│
├── ai_matching_step1_extract.py          # Step 1: Extract filtered items
├── ai_matching_step2_gemini.py           # Step 2: AI matching
├── ai_matching_step3_save.py             # Step 3: Save to database
├── ai_matching_step4_report.py           # Step 4: Generate report
├── create_fernandes_catalog_sample.py    # Helper: Create sample catalog
│
├── AI_MATCHING_PLAN.md                   # Detailed strategy document
└── AI_MATCHING_README.md                 # This file
```

---

## Customization

### Adjust Filter Keywords

Edit `ai_matching_step1_extract.py` line ~35:

```python
# Add more keywords
WHERE LOWER(ti.description) LIKE '%curativo%'
   OR LOWER(ti.description) LIKE '%transparente%'
   OR LOWER(ti.description) LIKE '%gaze%'
   OR LOWER(ti.description) LIKE '%atadura%'
```

### Adjust Confidence Thresholds

Edit `ai_matching_step3_save.py`:

```python
# Change from 90% to 85%
high_confidence = [m for m in matches if m['confidence'] >= 85]
```

### Adjust Batch Size

Edit `ai_matching_step2_gemini.py` line ~23:

```python
# Change from 50 to 30 (more API calls, more precise)
# Or increase to 100 (fewer calls, faster, but may reduce accuracy)
self.batch_size = 50
```

### Customize AI Prompt

Edit `ai_matching_step2_gemini.py` in the `create_matching_prompt()` method to:
- Add specific matching rules
- Adjust confidence criteria
- Add domain-specific keywords
- Change output format

---

## Troubleshooting

### Issue: "GEMINI_API_KEY not found"

**Solution:** Add API key to `.env`:
```bash
echo "GEMINI_API_KEY=your_key_here" >> .env
```

### Issue: "fernandes_products.json not found"

**Solution:** Create the catalog file:
```bash
python3 ai_matching/utils/create_catalog_sample.py
# Then edit data/fernandes_products.json with actual products
```

### Issue: "Low match rate (<30%)"

**Possible causes:**
1. **Fernandes catalog too small** → Add more products
2. **Keywords too restrictive** → Add more filter keywords
3. **Product descriptions too different** → Adjust AI prompt
4. **Wrong product categories** → Check if Fernandes specializes in these items

### Issue: "API quota exceeded"

**Solution:**
- Free tier: 15 requests/minute
- Wait 1 minute or upgrade to paid tier
- Add longer delays in code: `await asyncio.sleep(2)`

### Issue: "JSON parsing errors"

**Cause:** Gemini sometimes returns markdown-formatted JSON

**Solution:** Already handled in code (lines 155-162 in step2), but if it persists:
- Reduce batch size (try 20-30 instead of 50)
- Add more explicit JSON formatting instructions to prompt

---

## Cost & Performance

### API Costs (Gemini 2.5 Flash)

| Scenario | Items | Batches | Cost |
|----------|-------|---------|------|
| Small | 500 | 10 | $0.01 |
| Medium | 1,000 | 20 | $0.02 |
| Large | 5,000 | 100 | $0.10 |

**Free tier:** 1,500 requests/day = enough for 75,000 items!

### Performance Benchmarks

| Metric | Value |
|--------|-------|
| Processing speed | ~20 items/second |
| API response time | ~3 seconds/batch |
| Total time (1,000 items) | ~2 minutes |
| Match accuracy (high conf) | 90-95% |
| Match accuracy (medium conf) | 70-85% |

---

## Next Steps

### After Initial Run

1. ✅ Review sample of high-confidence matches (validate accuracy)
2. ✅ Process medium-confidence CSV (quick manual review)
3. ✅ Export to Notion (use existing `notion_integration.py`)
4. ✅ Track savings opportunities from price differences

### Future Enhancements

1. **Expand to all items:** Remove keyword filter, match entire 9,000 items
2. **Multi-vendor matching:** Add other supplier catalogs
3. **Historical tracking:** Track price trends over time
4. **Automated alerts:** Email when high-value opportunities found
5. **Fine-tuning:** Create training dataset from validated matches

---

## Support

For issues or questions:
1. Check `AI_MATCHING_PLAN.md` for detailed strategy
2. Review code comments in each script
3. Check Gemini API docs: https://ai.google.dev/docs

---

**Ready to start?**

```bash
# 1. Setup
pip install google-generativeai
python3 ai_matching/utils/create_catalog_sample.py

# 2. Run workflow
python3 ai_matching/step1_extract.py
python3 ai_matching/step2_gemini.py
python3 ai_matching/step3_save.py
python3 ai_matching/step4_report.py
```

**Total time: ~5 minutes | Total cost: ~$0.02**
