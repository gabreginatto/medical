# AI Matching Implementation Checklist

Quick checklist to get AI matching up and running.

---

## ☐ Phase 1: Setup (5 minutes)

### ☐ 1.1 Install Dependencies
```bash
pip install google-generativeai
```

### ☐ 1.2 Get Gemini API Key
- [ ] Go to https://makersuite.google.com/app/apikey
- [ ] Create new API key
- [ ] Copy the key

### ☐ 1.3 Add API Key to .env
```bash
echo "GEMINI_API_KEY=your_actual_api_key_here" >> .env
```

### ☐ 1.4 Verify Database Schema
```bash
python3 ai_matching/utils/check_schema.py
```

**Expected output:**
```
✅ tender_items table exists
✅ matched_products table exists
✅ fernandes_products table exists
```

---

## ☐ Phase 2: Prepare Fernandes Catalog (15 minutes)

### ☐ 2.1 Create Sample Catalog Template
```bash
python3 ai_matching/utils/create_catalog_sample.py
```

**This creates:** `data/fernandes_products.json` with sample data

### ☐ 2.2 Replace with Real Fernandes Products
- [ ] Open `data/fernandes_products.json`
- [ ] Replace sample products with your actual Fernandes catalog
- [ ] Ensure each product has:
  - `code`: Product code/SKU
  - `name`: Product name
  - `price`: Price in BRL
  - `category`: Category (optional)
  - `description`: Description (optional)

**Example format:**
```json
{
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

### ☐ 2.3 Verify Catalog
- [ ] Check file is valid JSON (no syntax errors)
- [ ] Verify all products have `code`, `name`, and `price`
- [ ] Minimum 10-20 products recommended for testing

---

## ☐ Phase 3: Run Matching Workflow (5 minutes)

### ☐ 3.1 Step 1: Extract Filtered Items
```bash
python3 ai_matching/step1_extract.py
```

**Verify:**
- [ ] See "Extraction Statistics" output
- [ ] File created: `data/filtered_items_for_matching.json`
- [ ] Item count looks reasonable (500-2,000 items)

**If item count is 0:**
- Check database has items with "curativo" or "transparente" in description
- Run: `SELECT COUNT(*) FROM tender_items WHERE LOWER(description) LIKE '%curativo%'`

---

### ☐ 3.2 Step 2: AI Matching with Gemini
```bash
python3 ai_matching/step2_gemini.py
```

**Verify:**
- [ ] See "Processing batch X/Y" messages
- [ ] See "Matching Statistics" at end
- [ ] File created: `data/ai_matches.json`
- [ ] Match rate is reasonable (>40%)

**Expected time:** 1-3 minutes for 1,000 items

**If errors occur:**
- Check `GEMINI_API_KEY` is set correctly
- Check internet connection
- Reduce batch size if getting timeouts

---

### ☐ 3.3 Step 3: Save Results to Database
```bash
python3 ai_matching/step3_save.py
```

**Verify:**
- [ ] See "Saved X high-confidence matches" message
- [ ] File created: `data/medium_confidence_matches_for_review.csv`
- [ ] Check database: `SELECT COUNT(*) FROM matched_products WHERE match_method = 'ai_gemini'`

---

### ☐ 3.4 Step 4: Generate Report
```bash
python3 ai_matching/step4_report.py
```

**Verify:**
- [ ] See "Matching Performance" statistics
- [ ] See "Price Comparison Analysis"
- [ ] See "Top Price Opportunities"

---

## ☐ Phase 4: Quality Check (10 minutes)

### ☐ 4.1 Validate Sample of High-Confidence Matches
```sql
-- Get 10 random high-confidence matches
SELECT
    ti.description as tender_item,
    fp.name as fernandes_product,
    mp.match_confidence,
    mp.match_reasoning
FROM matched_products mp
JOIN tender_items ti ON mp.tender_item_id = ti.id
JOIN fernandes_products fp ON mp.fernandes_product_id = fp.id
WHERE mp.match_method = 'ai_gemini'
  AND mp.match_confidence >= 90
ORDER BY RANDOM()
LIMIT 10;
```

**Check:**
- [ ] Matches look correct
- [ ] Dimensions/specs match
- [ ] Product types match
- [ ] Reasoning makes sense

**If matches look wrong:**
- Adjust AI prompt in `ai_matching_step2_gemini.py`
- Add more specific matching rules
- Re-run step 2-4

---

### ☐ 4.2 Review Medium-Confidence Matches
- [ ] Open `data/medium_confidence_matches_for_review.csv`
- [ ] Review first 10-20 matches
- [ ] Mark `accept` column with YES/NO
- [ ] Add notes if needed

**Quick review tips:**
- Compare product types (film, curativo, gaze, etc.)
- Check dimensions match
- Verify material/characteristics
- Look for brand names

---

## ☐ Phase 5: Refinement (Optional)

### ☐ 5.1 Adjust Filter Keywords (if needed)
If you want to match more items, edit `ai_matching_step1_extract.py`:

```python
WHERE LOWER(description) LIKE '%curativo%'
   OR LOWER(description) LIKE '%transparente%'
   OR LOWER(description) LIKE '%gaze%'
   OR LOWER(description) LIKE '%atadura%'
```

### ☐ 5.2 Adjust Confidence Thresholds (if needed)
If you want to auto-accept more matches, edit `ai_matching_step3_save.py`:

```python
# Change from 90 to 85
high_confidence = [m for m in matches if m['confidence'] >= 85]
```

### ☐ 5.3 Expand Fernandes Catalog
- [ ] Add more products to `data/fernandes_products.json`
- [ ] Include product variations
- [ ] Add all common medical supplies

---

## ☐ Phase 6: Integration (Future)

### ☐ 6.1 Export to Notion
- [ ] Use existing `notion_integration.py` to export matches
- [ ] Filter for high-value opportunities (big price differences)
- [ ] Create action items for purchasing team

### ☐ 6.2 Schedule Regular Runs
- [ ] Add to cron job or task scheduler
- [ ] Run weekly/monthly on new tender batches
- [ ] Auto-email reports to stakeholders

### ☐ 6.3 Track Savings
- [ ] Monitor price differences over time
- [ ] Calculate actual savings when switching to Fernandes
- [ ] Report ROI to management

---

## Success Criteria

**You're done when:**

✅ **Extraction (Step 1):**
- [ ] 500+ items filtered from database
- [ ] Statistics look reasonable

✅ **Matching (Step 2):**
- [ ] 50%+ match rate
- [ ] 70%+ high confidence matches
- [ ] Average confidence >80%

✅ **Quality (Validation):**
- [ ] Sample of 10 matches validated as correct
- [ ] Reasoning makes sense
- [ ] No obvious errors

✅ **Database (Step 3):**
- [ ] 200+ matches saved to `matched_products`
- [ ] Can query successfully

✅ **Report (Step 4):**
- [ ] Price analysis shows opportunities
- [ ] Top opportunities identified
- [ ] Ready for action

---

## Troubleshooting

### Common Issues

**"No items found" in Step 1**
- Check: `SELECT COUNT(*) FROM tender_items WHERE LOWER(description) LIKE '%curativo%'`
- If 0: Adjust filter keywords or check data

**"API key not found" in Step 2**
- Check: `.env` file has `GEMINI_API_KEY=...`
- Verify: No quotes around the key
- Test: `echo $GEMINI_API_KEY` (should show key)

**"Low match rate (<30%)" in Step 2**
- Add more products to Fernandes catalog
- Expand filter keywords
- Adjust AI prompt for your domain

**"JSON parsing errors" in Step 2**
- Reduce batch size from 50 to 20
- Add more explicit formatting instructions to prompt

**"Database errors" in Step 3**
- Run `check_db_schema_for_matching.py` to verify schema
- Check `fernandes_products` table has data
- Verify foreign key relationships

---

## Quick Commands Reference

```bash
# Setup
pip install google-generativeai
python3 ai_matching/utils/check_schema.py

# Create catalog
python3 ai_matching/utils/create_catalog_sample.py

# Run workflow
python3 ai_matching/step1_extract.py    # Extract
python3 ai_matching/step2_gemini.py     # Match
python3 ai_matching/step3_save.py       # Save
python3 ai_matching/step4_report.py     # Report

# Check results
SELECT COUNT(*) FROM matched_products WHERE match_method = 'ai_gemini';
```

---

## Time Estimates

| Phase | Time |
|-------|------|
| Setup | 5 min |
| Prepare Catalog | 15 min |
| Run Workflow | 5 min |
| Quality Check | 10 min |
| Review & Adjust | 15 min |
| **TOTAL** | **50 min** |

**vs Manual Matching: 75+ hours**

**ROI: 90x time savings**

---

## Next Steps After Completion

1. ✅ Export high-value opportunities to Notion
2. ✅ Share CSV review file with purchasing team
3. ✅ Schedule weekly/monthly runs for new tenders
4. ✅ Track savings and report ROI
5. ✅ Expand to other product categories
6. ✅ Add more supplier catalogs

---

**Ready to start?**

```bash
# 1. Verify setup
python3 ai_matching/utils/check_schema.py

# 2. Create catalog template
python3 ai_matching/utils/create_catalog_sample.py

# 3. Edit catalog with real products
# open data/fernandes_products.json

# 4. Run matching
python3 ai_matching/step1_extract.py
python3 ai_matching/step2_gemini.py
python3 ai_matching/step3_save.py
python3 ai_matching/step4_report.py
```

**Questions?** See `AI_MATCHING_README.md` for detailed guide.
