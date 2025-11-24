# Unified Medical Exhibitors Database - Migration Guide

## Overview

This guide walks through the safe migration from separate MEDICA and CMEF databases to a unified `medical_unified` database that combines both datasets with enhanced product categorization.

## 🎯 Goals

1. **Safety First**: Create new database WITHOUT touching existing `medical` database
2. **Unified Schema**: Single table with both MEDICA and CMEF companies
3. **Source Tracking**: Clear `data_source` field to distinguish origins
4. **Enhanced Search**: Product categories and keywords for both datasets

## 📊 Database Architecture

### New Table: `medical_exhibitors`

```sql
medical_exhibitors (
    -- Core fields from both sources
    id, name, company_name_zh, location, booth_number,
    email, phone, website, address, country, region,

    -- Event tracking
    event,          -- "MEDICA 2025" or "CMEF 2025"
    data_source,    -- "MEDICA" or "CMEF" (KEY FIELD)

    -- AI enrichment (NEW)
    product_category,        -- e.g., "Orthopedics & Rehabilitation"
    product_keywords[],      -- Searchable keywords array
    category_confidence,     -- 0.0 - 1.0

    -- Website validation (NEW)
    website_validated,
    website_status_code,

    -- Timestamps
    scraped_at, created_at, updated_at
)
```

### Key Features

- **GIN Index** on `product_keywords[]` for fast array search
- **Full-text search** on `company_description`
- **Views** for backward compatibility (`medica_exhibitors`, `cmef_exhibitors`)
- **Triggers** for automatic `updated_at` timestamp

## 🚀 Migration Steps

### Step 1: Create New Database

```bash
# Option A: Local PostgreSQL
createdb medical_unified

# Option B: Google Cloud SQL
gcloud sql databases create medical_unified \
  --instance=your-instance-name
```

### Step 2: Create Schema

```bash
cd /Users/gabrielreginatto/Desktop/Code/Medical/CMEF

# Run schema creation script
psql -h <host> -U postgres -d medical_unified -f create_unified_database.sql

# For Cloud SQL:
gcloud sql connect your-instance-name --user=postgres --database=medical_unified < create_unified_database.sql
```

**Expected Output:**
```
CREATE TABLE
CREATE INDEX (multiple)
CREATE VIEW (2)
CREATE FUNCTION
CREATE TRIGGER
```

**Verify Schema:**
```sql
-- Check table exists
\dt medical_exhibitors

-- Check all columns
\d medical_exhibitors

-- Check indexes
\di

-- Should show 10+ indexes including GIN index on product_keywords
```

### Step 3: Migrate MEDICA Data

**IMPORTANT**: This step READS from old database (no modifications!)

```bash
# Set environment variables (recommended)
export SOURCE_DB_URL="postgresql://user:password@host:5432/medical"
export TARGET_DB_URL="postgresql://user:password@host:5432/medical_unified"

# Run migration
python3 migrate_medica_to_unified.py
```

**OR** run interactively:
```bash
python3 migrate_medica_to_unified.py
# Prompts for:
# 1. Source database URL (old 'medical' database)
# 2. Target database URL (new 'medical_unified' database)
# 3. Confirmation before proceeding
```

**Expected Output:**
```
=======================================================================
MEDICA DATA MIGRATION TO UNIFIED DATABASE
=======================================================================
Source: host:5432/medical
Target: host:5432/medical_unified
=======================================================================

📡 Connecting to databases...
📖 Reading MEDICA data from source database...
✅ Found 1,321 MEDICA companies to migrate
📋 Sample company: 3M Deutschland GmbH

💾 Inserting 1,321 companies into unified database...
  Migrated 100/1321 companies
  Migrated 200/1321 companies
  ...
  Migrated 1321/1321 companies

✅ Successfully migrated 1,321 MEDICA companies

🔍 Verifying migration...
  Source database: 1321 companies
  Target database: 1321 MEDICA companies
  ✅ Counts match - migration successful!
  ✅ Sample record verified: 3M Deutschland GmbH

=======================================================================
UNIFIED DATABASE SUMMARY
=======================================================================

By Data Source:
  MEDICA: 1321 companies (0 classified)

By Event:
  MEDICA 2025 (MEDICA): 1321

✅ MEDICA migration completed successfully!
```

**Verify Migration:**
```sql
-- Check MEDICA data
SELECT COUNT(*) FROM medical_exhibitors WHERE data_source = 'MEDICA';
-- Should return: 1321

-- Sample query
SELECT name, country, website FROM medical_exhibitors WHERE data_source = 'MEDICA' LIMIT 5;
```

### Step 4: Import CMEF Data

```bash
# Set environment variable
export UNIFIED_DB_URL="postgresql://user:password@host:5432/medical_unified"

# Run import
python3 import_cmef_to_unified.py
```

**OR** run interactively:
```bash
python3 import_cmef_to_unified.py
# Prompts for:
# 1. Unified database URL
# 2. Confirmation before proceeding
```

**Expected Output:**
```
=======================================================================
CMEF → UNIFIED DATABASE IMPORT
=======================================================================

📖 Loading CMEF data from data/enriched_companies.json...
✅ Loaded 4,497 CMEF companies

📋 Sample company:
  Name: A.R. Medicom Inc. Healthcare (Shanghai) Ltd.
  Chinese: None
  Booth: 5.2H25
  Category: Disposable Medical Supplies
  Keywords: ['infection control products', 'personal protective products', ...]

📡 Connecting to unified database...

💾 Inserting 4,497 CMEF companies...
  Imported 100/4497 companies
  Imported 200/4497 companies
  ...
  Imported 4497/4497 companies

✅ Successfully imported 4,497 CMEF companies

=======================================================================
UNIFIED DATABASE SUMMARY
=======================================================================

By Data Source:
  CMEF: 4497 companies (4497 classified, avg confidence: 0.85)
  MEDICA: 1321 companies (0 classified)

By Event:
  CMEF 2025 (CMEF): 4497
  MEDICA 2025 (MEDICA): 1321

Top 10 CMEF Categories:
  Diagnostic Equipment: 823
  Orthopedics & Rehabilitation: 654
  Surgical Instruments: 512
  ...

=======================================================================
TOTAL: 5818 companies
CLASSIFIED: 4497 companies (77.3%)
=======================================================================

✅ CMEF import completed successfully!
```

**Verify Import:**
```sql
-- Check CMEF data
SELECT COUNT(*) FROM medical_exhibitors WHERE data_source = 'CMEF';
-- Should return: 4497

-- Check total
SELECT COUNT(*) FROM medical_exhibitors;
-- Should return: 5818

-- Sample CMEF query
SELECT name, company_name_zh, booth_number, product_category
FROM medical_exhibitors
WHERE data_source = 'CMEF'
LIMIT 5;
```

### Step 5: Classify MEDICA Companies

Now enrich existing MEDICA companies with product categories using the same AI classification as CMEF.

```bash
# Set environment variable
export UNIFIED_DB_URL="postgresql://user:password@host:5432/medical_unified"

# Run classification
python3 classify_unified_companies.py
```

**Interactive Options:**
```
=======================================================================
CLASSIFICATION OPTIONS
=======================================================================
1. Classify MEDICA companies only
2. Classify CMEF companies only
3. Classify ALL companies
=======================================================================

Select option (1-3): 1
```

**Expected Output:**
```
=======================================================================
UNIFIED DATABASE CLASSIFICATION
=======================================================================
Target: MEDICA
Model: gemini-2.5-flash
=======================================================================

📊 Found 1,321 companies to classify
  MEDICA: 1321 companies

🤖 Classifying companies using Gemini AI...
  Progress: 10/1321 (10 success, 0 errors)
  Progress: 20/1321 (20 success, 0 errors)
  ...
  Progress: 1321/1321 (1315 success, 6 errors)

✅ Classification complete!
  Success: 1315
  Errors: 6

=======================================================================
UNIFIED DATABASE SUMMARY
=======================================================================

By Data Source:
  CMEF: 4497 companies
    Classified: 4497 (100.0%)
    Avg Confidence: 0.85
  MEDICA: 1321 companies
    Classified: 1315 (99.5%)
    Avg Confidence: 0.82

Top 15 Product Categories (Unified):
  Diagnostic Equipment: 1245 (MEDICA: 422, CMEF: 823)
  Orthopedics & Rehabilitation: 987 (MEDICA: 333, CMEF: 654)
  Surgical Instruments: 756 (MEDICA: 244, CMEF: 512)
  ...

=======================================================================
TOTAL COMPANIES: 5818
CLASSIFIED: 5812 (99.9%)
UNCLASSIFIED: 6 (0.1%)
=======================================================================

✅ Classification completed successfully!
```

**Verify Classification:**
```sql
-- Check classification status
SELECT
    data_source,
    COUNT(*) as total,
    COUNT(product_category) as classified,
    COUNT(*) - COUNT(product_category) as unclassified
FROM medical_exhibitors
GROUP BY data_source;

-- Expected:
-- CMEF    | 4497 | 4497 | 0
-- MEDICA  | 1321 | 1315 | 6
```

## ✅ Verification Checklist

After completing all steps, verify the migration:

```sql
-- 1. Total count
SELECT COUNT(*) FROM medical_exhibitors;
-- Expected: 5818 (1321 MEDICA + 4497 CMEF)

-- 2. By data source
SELECT data_source, COUNT(*)
FROM medical_exhibitors
GROUP BY data_source;
-- Expected: MEDICA: 1321, CMEF: 4497

-- 3. Classification rate
SELECT
    ROUND(COUNT(product_category)::numeric / COUNT(*) * 100, 1) as classified_pct
FROM medical_exhibitors;
-- Expected: ~99.9%

-- 4. Test keyword search
SELECT name, product_category, data_source
FROM medical_exhibitors
WHERE 'wheelchair' = ANY(product_keywords)
LIMIT 10;
-- Should return companies from both MEDICA and CMEF

-- 5. Test category search
SELECT data_source, COUNT(*)
FROM medical_exhibitors
WHERE product_category = 'Diagnostic Equipment'
GROUP BY data_source;
-- Should show companies from both sources

-- 6. Test full-text search
SELECT name, data_source, product_category
FROM medical_exhibitors
WHERE to_tsvector('english', company_description) @@ to_tsquery('english', 'ultrasound & imaging')
LIMIT 10;
-- Should return relevant companies

-- 7. Check views
SELECT COUNT(*) FROM medica_exhibitors;  -- Should be 1321
SELECT COUNT(*) FROM cmef_exhibitors;    -- Should be 4497
```

## 🎨 Example Queries

### Search by Product Keyword
```sql
SELECT name, data_source, product_category, website
FROM medical_exhibitors
WHERE 'ultrasound' = ANY(product_keywords)
ORDER BY category_confidence DESC;
```

### Compare MEDICA vs CMEF by Category
```sql
SELECT
    product_category,
    COUNT(*) FILTER (WHERE data_source = 'MEDICA') as medica_count,
    COUNT(*) FILTER (WHERE data_source = 'CMEF') as cmef_count,
    COUNT(*) as total_count
FROM medical_exhibitors
WHERE product_category IS NOT NULL
GROUP BY product_category
ORDER BY total_count DESC
LIMIT 20;
```

### Find Companies by Booth Number
```sql
SELECT name, company_name_zh, booth_number, product_category
FROM medical_exhibitors
WHERE booth_number LIKE '5.2%'
  AND data_source = 'CMEF'
ORDER BY booth_number;
```

### Full-Text Search
```sql
SELECT name, data_source, product_category,
       ts_rank(to_tsvector('english', company_description),
               to_tsquery('english', 'surgical & robotic')) as rank
FROM medical_exhibitors
WHERE to_tsvector('english', company_description) @@ to_tsquery('english', 'surgical & robotic')
ORDER BY rank DESC
LIMIT 20;
```

## 📈 Next Steps

### 1. Update Looker Connection

Update Looker Studio to point to new `medical_unified` database:

1. Go to Looker Studio
2. Data Sources → Edit connection
3. Update database name: `medical` → `medical_unified`
4. Test connection

### 2. Update Looker Views

Create new views in Looker to leverage new fields:

```sql
-- /Users/gabrielreginatto/Desktop/Code/Medical/CMEF/looker_views_unified.sql

view: medical_exhibitors {
  sql_table_name: medical_exhibitors ;;

  dimension: data_source {
    type: string
    sql: ${TABLE}.data_source ;;
  }

  dimension: product_category {
    type: string
    sql: ${TABLE}.product_category ;;
  }

  dimension: product_keywords {
    type: string
    sql: ARRAY_TO_STRING(${TABLE}.product_keywords, ', ') ;;
  }

  dimension: category_confidence {
    type: number
    sql: ${TABLE}.category_confidence ;;
  }

  measure: count_companies {
    type: count
  }

  measure: avg_confidence {
    type: average
    sql: ${category_confidence} ;;
  }
}
```

### 3. Create Unified Dashboards

Build dashboards with:
- **Data Source Filter**: Toggle between MEDICA/CMEF/Both
- **Category Breakdown**: Pie charts by product category
- **Keyword Search**: Input field for product keywords
- **Geographic View**: Map by country/region
- **Comparison View**: MEDICA vs CMEF side-by-side

## 🔄 Rollback Plan

If issues occur, the old `medical` database is untouched:

```bash
# Option 1: Drop new database (clean slate)
dropdb medical_unified

# Option 2: Restore specific table
DROP TABLE medical_exhibitors CASCADE;

# Option 3: Keep new database, point Looker back to old one
# No code changes needed - just update Looker connection
```

## 📝 File Reference

| File | Purpose |
|------|---------|
| `create_unified_database.sql` | Create new database schema |
| `migrate_medica_to_unified.py` | Copy MEDICA data (read-only) |
| `import_cmef_to_unified.py` | Import CMEF data |
| `classify_unified_companies.py` | Classify all companies |
| `MIGRATION_GUIDE.md` | This file |

## ⚠️ Important Notes

1. **Safety**: Original `medical` database is NEVER modified
2. **Data Loss**: No risk - all operations are INSERT/UPDATE in new database
3. **Rollback**: Simply drop `medical_unified` and point Looker back
4. **Performance**: GIN indexes ensure fast keyword search
5. **Cost**: Gemini API calls for classification (~1,321 MEDICA companies)

## 🎉 Success Criteria

- ✅ New `medical_unified` database created
- ✅ 1,321 MEDICA companies migrated
- ✅ 4,497 CMEF companies imported
- ✅ ~5,812 companies classified (99.9%)
- ✅ Keyword search working
- ✅ Views for backward compatibility
- ✅ Old database untouched and intact

## 🆘 Troubleshooting

### Issue: "relation 'medical_exhibitors' does not exist"
**Solution**: Run `create_unified_database.sql` first

### Issue: "connection refused"
**Solution**: Check database URL and credentials

### Issue: Classification is slow
**Solution**: Normal - Gemini processes ~10 companies/second. 1,321 companies ≈ 2-3 minutes

### Issue: Some companies not classified
**Solution**: Companies without descriptions cannot be classified. This is expected for ~6 companies.

### Issue: Looker not showing new data
**Solution**:
1. Update connection to `medical_unified`
2. Clear Looker cache
3. Refresh data source schema

## 📞 Support

For issues:
1. Check logs in `/Users/gabrielreginatto/Desktop/Code/Medical/CMEF/logs/`
2. Verify database connection: `psql -h <host> -U postgres -d medical_unified -c "SELECT COUNT(*) FROM medical_exhibitors;"`
3. Review error messages in console output
