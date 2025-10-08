# AI-Powered Product Matching Plan
## Using Gemini 2.5 Flash for Fernandes Product Matching

---

## Problem Statement

**Current Situation:**
- ~9,000 tender items in database with homologated prices
- Fernandes product catalog with standardized names
- Product name variations make direct string matching ineffective
- Example variations:
  - DB: "Curativo adesivo transparente 10x12cm"
  - Fernandes: "Filme Transparente Tegaderm 10x12"
  - These should match but differ significantly in naming

**Goal:**
Match tender items to Fernandes products using AI to handle name variations

---

## Strategy: Two-Stage Filtering + AI Matching

### Stage 1: Database Filtering (Fast, SQL-based)
**Filter:** Items containing keywords "curativo" OR "transparente"

**Rationale:**
- Fernandes specializes in curativos (dressings/bandages)
- Many products are transparent films/dressings
- Reduces ~9,000 items to estimated ~500-1,500 items
- **99% cost reduction** for API calls

**SQL Query:**
```sql
SELECT id, description, quantity, homologated_unit_value, tender_id
FROM tender_items
WHERE LOWER(description) LIKE '%curativo%'
   OR LOWER(description) LIKE '%transparente%'
ORDER BY homologated_unit_value DESC;
```

---

### Stage 2: AI-Powered Matching (Gemini 2.5 Flash)

**Model Choice:** `gemini-2.0-flash-exp`
- **Speed:** ~1000 tokens/sec
- **Cost:** $0.075 per 1M input tokens, $0.30 per 1M output tokens
- **Context:** 1M tokens (can process many items in batch)
- **Reasoning:** Fast, cheap, great for classification/matching tasks

**Matching Approach:**

#### Option A: Batch Matching (Recommended)
Send 20-50 filtered items + full Fernandes catalog per API call

**Advantages:**
- Fewer API calls (20-75 calls vs 500-1,500)
- Lower cost ($0.50 - $2.00 total)
- Faster processing (2-5 minutes total)

**Prompt Structure:**
```
You are a medical product matching expert. Match tender items to Fernandes products.

FERNANDES CATALOG:
1. Filme Transparente Tegaderm 10x12cm - Code: FT1012
2. Curativo Hidrocoloide 10x10cm - Code: CH1010
3. ...

TENDER ITEMS TO MATCH:
1. [ID: 123] "Curativo adesivo transparente 10x12cm" - R$ 5.50
2. [ID: 456] "Film transparente esteril tegaderm 10x12" - R$ 6.20
3. ...

INSTRUCTIONS:
- Match each tender item to the most similar Fernandes product
- Consider: product type, dimensions, material, brand
- Return ONLY matches with 80%+ confidence
- Output format: JSON array

OUTPUT FORMAT:
[
  {
    "tender_item_id": 123,
    "fernandes_code": "FT1012",
    "confidence": 95,
    "reasoning": "Exact match: transparent film dressing, same dimensions"
  },
  {
    "tender_item_id": 456,
    "fernandes_code": "FT1012",
    "confidence": 92,
    "reasoning": "Same product (Tegaderm), variant spelling, same size"
  }
]
```

#### Option B: Individual Matching
Send 1 tender item + catalog per call

**Advantages:**
- More precise per-item reasoning
- Easier error handling
- Better for complex cases

**Disadvantages:**
- More API calls (500-1,500 calls)
- Higher cost ($5-$15)
- Slower (10-20 minutes)

---

### Stage 3: Confidence-Based Filtering

**Tier 1: Auto-Accept (Confidence ≥ 90%)**
- Save directly to `matched_products` table
- Flag as AI-matched
- Ready for export to Notion

**Tier 2: Review Queue (70% ≤ Confidence < 90%)**
- Save to `matched_products_pending` table
- Requires manual review
- Export to CSV for quick review

**Tier 3: Reject (Confidence < 70%)**
- Don't save
- Log for future re-processing with better prompts

---

## Expected Results

### Cost Estimation

**Scenario: 1,000 filtered items, Batch matching (50 items/call)**

**Input tokens per call:**
- Fernandes catalog: ~5,000 tokens (200 products × 25 tokens)
- Tender items (50): ~2,500 tokens (50 × 50 tokens)
- Prompt: ~500 tokens
- **Total input:** ~8,000 tokens/call

**Output tokens per call:**
- JSON matches (50): ~2,000 tokens
- **Total output:** ~2,000 tokens/call

**Total API calls:** 1,000 items ÷ 50 = 20 calls

**Cost calculation:**
- Input: 20 calls × 8,000 tokens = 160,000 tokens = $0.012
- Output: 20 calls × 2,000 tokens = 40,000 tokens = $0.012
- **Total cost: ~$0.02** (essentially free!)

**Time estimation:**
- 20 API calls × 3 seconds/call = 60 seconds
- **Total time: ~1 minute**

---

### Quality Estimation

**Expected match rates (based on product categories):**

**High confidence (≥90%):**
- Curativos transparentes: 80-90% (standardized dimensions)
- Branded products (Tegaderm, etc.): 85-95% (clear brand names)
- **Estimated: 400-600 items (~50%)**

**Medium confidence (70-89%):**
- Generic curativos: 60-70% (variable descriptions)
- Non-branded items: 50-60%
- **Estimated: 200-300 items (~25%)**

**Low confidence (<70%):**
- Ambiguous descriptions: 20-30%
- Missing dimensions/specs: 30-40%
- **Estimated: 200-300 items (~25%)**

**Net result:**
- **400-600 high-quality matches** ready for Notion export
- **200-300 items** for quick manual review
- **Massive time savings** vs manual matching of 9,000 items

---

## Implementation Plan

### Phase 1: Data Extraction
1. ✅ Query filtered items from database
2. ✅ Load Fernandes catalog from CSV/database
3. ✅ Prepare data structures for API

### Phase 2: AI Matching
1. ✅ Configure Gemini API client
2. ✅ Create matching prompt template
3. ✅ Implement batch processing
4. ✅ Add retry logic for API failures
5. ✅ Parse and validate JSON responses

### Phase 3: Results Processing
1. ✅ Filter by confidence tiers
2. ✅ Save high-confidence matches to DB
3. ✅ Export review queue to CSV
4. ✅ Generate statistics report

### Phase 4: Validation & Review
1. ✅ Sample 10-20 matches for quality check
2. ✅ Review medium-confidence matches
3. ✅ Adjust prompts if needed
4. ✅ Re-run on rejected items with improved prompts

---

## Alternative Filters (Future Enhancements)

If "curativo" OR "transparente" doesn't capture enough items:

**Additional keywords:**
- "gaze", "atadura", "compressa", "adesivo"
- "esparadrapo", "band aid", "penso"
- "algodão", "swab", "tampão"
- "luva", "mascara", "equipo"

**Fernandes product categories:**
```sql
-- Dynamically build filter from Fernandes products
SELECT DISTINCT
    LOWER(REGEXP_SPLIT_TO_TABLE(product_name, ' ')) as keyword
FROM fernandes_products
WHERE LENGTH(REGEXP_SPLIT_TO_TABLE(product_name, ' ')) > 4
GROUP BY keyword
HAVING COUNT(*) >= 3;
```

This generates keywords from Fernandes catalog itself!

---

## Risk Mitigation

### Risk 1: Low Match Rate
**Mitigation:**
- Start with 100-item test batch
- Validate match quality manually
- Adjust prompt/filters before full run

### Risk 2: API Costs
**Mitigation:**
- Set hard limit: 100 API calls max on first run
- Monitor costs in Google Cloud Console
- Use streaming for better control

### Risk 3: False Positives
**Mitigation:**
- Require ≥90% confidence for auto-accept
- Manual review for 70-89% confidence
- Log all reasoning for auditability

### Risk 4: Rate Limiting
**Mitigation:**
- Gemini Flash has 1,500 RPM limit
- Our 20 calls = well under limit
- Add 100ms delay between calls anyway

---

## Success Metrics

**Quantitative:**
- Match rate: ≥50% of filtered items matched
- High confidence: ≥70% of matches above 90%
- Cost: <$1.00 total
- Time: <5 minutes end-to-end

**Qualitative:**
- Manual review confirms AI matches are accurate
- Faster than manual matching
- Repeatable for future tender batches

---

## Next Steps

1. **Extract filtered items** → `ai_matching_step1_extract.py`
2. **Run AI matching** → `ai_matching_step2_gemini.py`
3. **Save results** → `ai_matching_step3_save.py`
4. **Generate report** → `ai_matching_step4_report.py`

---

## Future Enhancements

### Enhancement 1: Multi-Vendor Matching
Expand beyond Fernandes to other medical suppliers

### Enhancement 2: Price Anomaly Detection
Use AI to flag suspiciously high/low prices

### Enhancement 3: Continuous Learning
Build training dataset from validated matches
Fine-tune model on medical product domain

### Enhancement 4: Semantic Search
Use embeddings (text-embedding-004) for similarity search
Pre-filter candidates before AI matching

---

## Estimated Total Impact

**Before (Manual Matching):**
- Time: 9,000 items × 30 sec = 75 hours
- Cost: Engineer time + fatigue errors
- Coverage: Maybe 20-30% reviewed

**After (AI Matching):**
- Time: 5 minutes automated + 30 min review = 35 minutes
- Cost: <$1 API + engineer time
- Coverage: 70-80% matched automatically

**ROI: 100x time savings, 95% cost reduction**
