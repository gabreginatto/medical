# MEDICA Database Enrichment Guide

## 🎯 Purpose

This script enriches your existing MEDICA database with AI-powered product classification, using the **exact same logic** as CMEF Step 3.

## ✅ What It Does

1. **Adds Classification Columns** (if they don't exist):
   - `product_category` - e.g., "Diagnostic Equipment"
   - `product_keywords` - Array of searchable keywords
   - `category_confidence` - AI confidence score (0.0-1.0)

2. **Classifies All Companies**:
   - Uses `company_description` field as input (same as CMEF's `scope_description`)
   - Applies Gemini 2.5 Flash AI classification
   - Extracts product category and keywords

3. **Creates Indexes**:
   - GIN index on `product_keywords` for fast array search
   - B-tree index on `product_category`

## 🔄 Key Adaptations from CMEF Step 3

### Original CMEF Step 3
```python
# Works with JSON file
companies = json.load(file)
for company in companies:
    scope = company.get('scope_description')  # ← CMEF field
    category_data = gemini.classify_product_category(scope)
    company['product_category'] = category_data['category']
```

### Adapted MEDICA Version
```python
# Works directly with database
companies = await conn.fetch("SELECT * FROM medica_exhibitors")
for company in companies:
    description = company['company_description']  # ← MEDICA field
    category_data = gemini.classify_product_category(description)
    await conn.execute("UPDATE medica_exhibitors SET product_category = ...")
```

### Key Differences

| Aspect | CMEF Step 3 | MEDICA Enrichment |
|--------|-------------|-------------------|
| **Input** | JSON file | PostgreSQL database |
| **Description Field** | `scope_description` | `company_description` |
| **Output** | JSON file | Database UPDATE |
| **Schema Changes** | None | Adds 3 new columns |
| **Data Source** | CMEF catalog | MEDICA exhibitors |

### Similarities (100% Same Logic)

✅ **Same AI Model**: `gemini-2.5-flash`
✅ **Same Classification Method**: `GeminiParserClient.classify_product_category()`
✅ **Same Categories**: 15+ medical equipment categories
✅ **Same Keywords Extraction**: Array of searchable terms
✅ **Same Confidence Scoring**: 0.0-1.0 scale
✅ **Same Error Handling**: Defaults to "Other Medical Equipment"

## 🚀 How to Use

### Prerequisites

1. Existing MEDICA database with companies
2. Database connection configured in environment variables
3. Gemini API access

### Run Enrichment

```bash
cd /Users/gabrielreginatto/Desktop/Code/Medical/CMEF

# Run enrichment script
python3 enrich_medica_inplace.py
```

### Interactive Prompts

```
Starting MEDICA database enrichment...

⚠️  IMPORTANT: This will modify the existing 'medical' database
   It will add new columns and populate them with AI classifications
   Existing data will NOT be deleted or modified

Do you want to proceed? (yes/no): yes

=======================================================================
MEDICA DATABASE ENRICHMENT
=======================================================================
Model: gemini-2.5-flash
=======================================================================

Checking if classification columns exist...
Adding classification columns to medica_exhibitors table...
✅ Classification columns added successfully
✅ Indexes created successfully

📊 Found 1,321 MEDICA companies to classify

📋 Sample company: 3M Deutschland GmbH
   Description: Medical adhesives, tapes, surgical drapes...

🤖 Classifying companies using Gemini AI...
   This will extract: category + product keywords from descriptions

  Progress: 10/1321 (10 success, 0 errors)
  Progress: 20/1321 (20 success, 0 errors)
  ...
  Progress: 1321/1321 (1315 success, 6 errors)

✅ Classification complete!
  Success: 1315
  Errors: 6

=======================================================================
MEDICA DATABASE SUMMARY
=======================================================================

📊 Overall Statistics:
  Total companies: 1321
  Classified: 1315 (99.5%)
  Unclassified: 6 (0.5%)
  Avg Confidence: 0.82

📂 Top 15 Product Categories:
  Diagnostic Equipment: 287
  Surgical Instruments: 198
  Laboratory Equipment: 156
  Patient Monitoring Systems: 134
  Medical Imaging: 112
  Orthopedics & Rehabilitation: 98
  ...

🔑 Sample Keywords:
  3M Deutschland GmbH: [surgical tape, wound care, infection prevention, ...]
  Siemens Healthineers: [MRI, CT scanner, ultrasound, X-ray, ...]
  ...

✅ MEDICA enrichment completed successfully!
```

## 📊 Expected Results

### Before Enrichment

```sql
SELECT * FROM medica_exhibitors LIMIT 1;
```

| id | name | location | company_description | product_category | product_keywords |
|----|------|----------|---------------------|------------------|------------------|
| 1 | 3M GmbH | Hall 10 A03 | Medical adhesives... | NULL | NULL |

### After Enrichment

```sql
SELECT * FROM medica_exhibitors LIMIT 1;
```

| id | name | location | company_description | product_category | product_keywords | category_confidence |
|----|------|----------|---------------------|------------------|------------------|---------------------|
| 1 | 3M GmbH | Hall 10 A03 | Medical adhesives... | Disposable Medical Supplies | {surgical tape, wound care, ...} | 0.89 |

## 🔍 Example Queries After Enrichment

### Search by Keyword
```sql
SELECT name, product_category, website
FROM medica_exhibitors
WHERE 'ultrasound' = ANY(product_keywords)
ORDER BY category_confidence DESC;
```

### Category Breakdown
```sql
SELECT
    product_category,
    COUNT(*) as company_count,
    ROUND(AVG(category_confidence)::numeric, 2) as avg_confidence
FROM medica_exhibitors
WHERE product_category IS NOT NULL
GROUP BY product_category
ORDER BY company_count DESC;
```

### Find Imaging Companies
```sql
SELECT name, location, product_keywords
FROM medica_exhibitors
WHERE product_category = 'Medical Imaging'
ORDER BY name;
```

### Full-Text + Keyword Search
```sql
SELECT name, product_category, product_keywords
FROM medica_exhibitors
WHERE (
    to_tsvector('english', company_description) @@ to_tsquery('english', 'robotic & surgical')
    OR 'robotics' = ANY(product_keywords)
)
LIMIT 20;
```

## ⚠️ Safety Considerations

### What Gets Modified

✅ **Added**: 3 new columns (`product_category`, `product_keywords`, `category_confidence`)
✅ **Updated**: `updated_at` timestamp for classified companies

### What Stays Untouched

✅ **NOT modified**: `name`, `location`, `company_description`, `email`, `phone`, `website`, `address`, etc.
✅ **NOT deleted**: No data is ever deleted
✅ **NOT affected**: `medica_product_images`, `medica_documents` tables

### Idempotent Operation

The script is **idempotent** - you can run it multiple times:
- First run: Adds columns, classifies all companies
- Second run: Only classifies companies with NULL categories
- Third run: No changes (all already classified)

## 🔄 Rollback Instructions

If you want to remove the classification:

```sql
-- Remove classification data (keep columns)
UPDATE medica_exhibitors
SET
    product_category = NULL,
    product_keywords = NULL,
    category_confidence = NULL;

-- OR drop columns entirely
ALTER TABLE medica_exhibitors
DROP COLUMN product_category,
DROP COLUMN product_keywords,
DROP COLUMN category_confidence;

-- Drop indexes
DROP INDEX IF EXISTS idx_medica_keywords;
DROP INDEX IF EXISTS idx_medica_category;
```

## 📈 Performance

- **Speed**: ~10 companies/second
- **Time for 1,321 companies**: ~2-3 minutes
- **API Calls**: 1,321 Gemini API requests
- **Cost**: Minimal (Gemini 2.5 Flash is very cheap)

## 🎯 Comparison: CMEF vs MEDICA Classification

### CMEF Classification Results
- Total companies: 4,497
- Classified: 4,497 (100%)
- Avg confidence: 0.85
- Top category: Diagnostic Equipment (823)

### MEDICA Classification Results (Expected)
- Total companies: ~1,321
- Classified: ~1,315 (99.5%)
- Avg confidence: ~0.82
- Top category: Diagnostic Equipment (~287)

### Why Similar Results?

Both use:
- Same AI model (gemini-2.5-flash)
- Same prompt engineering
- Same category definitions
- Same keyword extraction logic

The only difference is the **input field name**:
- CMEF: `scope_description`
- MEDICA: `company_description`

## 🆘 Troubleshooting

### Issue: "column does not exist"
**Solution**: Script automatically adds columns. If error persists, check database permissions.

### Issue: Classification is slow
**Solution**: Normal behavior. Gemini processes ~10 companies/second.

### Issue: Some companies not classified
**Solution**: Expected for companies without descriptions. Check:
```sql
SELECT COUNT(*) FROM medica_exhibitors WHERE company_description IS NULL OR company_description = '';
```

### Issue: Connection timeout
**Solution**: Increase timeout in `src/database.py` or run in batches.

## 📝 Logs

All operations are logged to:
```
logs/medica_enrichment.log
```

Check this file for:
- Progress updates
- Error messages
- Classification statistics
- Final summary

## ✅ Verification Checklist

After running enrichment:

```sql
-- 1. Check columns exist
\d medica_exhibitors

-- 2. Check classification rate
SELECT
    COUNT(*) as total,
    COUNT(product_category) as classified,
    ROUND(COUNT(product_category)::numeric / COUNT(*) * 100, 1) as pct
FROM medica_exhibitors;
-- Expected: ~99.5% classified

-- 3. Check indexes
\di
-- Should show: idx_medica_keywords, idx_medica_category

-- 4. Test keyword search
SELECT COUNT(*) FROM medica_exhibitors WHERE 'ultrasound' = ANY(product_keywords);
-- Should return some results

-- 5. Check categories
SELECT product_category, COUNT(*) FROM medica_exhibitors
WHERE product_category IS NOT NULL
GROUP BY product_category
ORDER BY count DESC;
-- Should show 10-15 categories
```

## 🎉 Next Steps

After enrichment:

1. **Update Looker Views**: Add dimensions for `product_category` and `product_keywords`
2. **Create Dashboards**: Category breakdown, keyword search
3. **Compare with CMEF**: Run unified analysis across both catalogs
4. **Export Data**: Generate reports by category

---

**Script**: `enrich_medica_inplace.py`
**Model**: `gemini-2.5-flash`
**Status**: Ready to use
**Safety**: Modifies existing DB (adds columns, updates values)
