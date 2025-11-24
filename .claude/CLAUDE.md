# Database Creation and Schema Implementation Guide

## 🎯 Purpose
This guide documents the **exact steps** to create a new Cloud SQL database, apply schema, and import data **without authentication errors**.

## ⚠️ Key Lessons Learned

### Authentication Issues Solved
1. **Service Account Key Location**: Must be in `/config/pncp-key.json` (not root)
2. **Environment Variables**: Must load `.env` file with `set -a && source .env && set +a`
3. **Database Manager**: Use existing `create_db_manager_from_env()` infrastructure
4. **Override Database Name**: Set `db_manager.database_name = 'medical_exhibitors'` after creation

### Common Errors Avoided
- ❌ `File pncp-key.json was not found` → Fixed with correct path
- ❌ `Missing required environment variables` → Fixed by sourcing .env
- ❌ `password authentication failed` → Fixed by using Cloud SQL Connector + IAM
- ❌ `invalid literal for int()` → Fixed by URL-encoding passwords (not needed with IAM)

## 📋 Step-by-Step Process

### Step 1: Create New Database on Cloud SQL

```bash
# Create database (uses your existing Cloud SQL instance)
gcloud sql databases create medical_exhibitors \
  --instance=pncp-medical-db \
  --project=medical-473219
```

**Expected Output:**
```
instance: pncp-medical-db
name: medical_exhibitors
project: medical-473219
Created database [medical_exhibitors].
```

### Step 2: Verify Database Creation

```bash
# List databases to confirm
gcloud sql databases list --instance=pncp-medical-db --project=medical-473219

# Should show:
# medical_exhibitors
# pncp_medical_data
# postgres
```

### Step 3: Prepare Python Import Script

**Key Requirements:**
- Use existing `CloudSQLManager` from `src/database.py`
- Override `database_name` attribute to target new database
- Handle NULL values (skip companies without names)
- Use async transactions for reliability

**Script Structure:**
```python
#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import create_db_manager_from_env

async def setup_database():
    # Connect using existing infrastructure
    db_manager = create_db_manager_from_env()

    # Override database name
    db_manager.database_name = 'medical_exhibitors'

    # Get connection
    conn = await db_manager.get_connection()

    try:
        # Create schema
        await conn.execute("CREATE TABLE IF NOT EXISTS ...")

        # Import data with NULL checks
        async with conn.transaction():
            for company in companies:
                if not company.get('name'):  # Skip NULL names
                    continue
                await conn.execute(insert_sql, ...)
    finally:
        await conn.close()
```

### Step 4: Run Import Script

**IMPORTANT**: Must run from parent directory with environment loaded

```bash
# Navigate to project root
cd /Users/gabrielreginatto/Desktop/Code/Medical

# Load environment + set credentials + run script
set -a && \
source .env && \
export GOOGLE_APPLICATION_CREDENTIALS="/Users/gabrielreginatto/Desktop/Code/Medical/config/pncp-key.json" && \
set +a && \
python3 CMEF/auto_setup_unified_db.py 2>&1 | tee CMEF/logs/auto_unified_setup.log
```

**Why This Works:**
1. `set -a` → Export all variables when sourcing
2. `source .env` → Load `GOOGLE_CLOUD_PROJECT`, `CLOUD_SQL_INSTANCE`, etc.
3. `export GOOGLE_APPLICATION_CREDENTIALS` → Override .env path with correct location
4. `set +a` → Stop auto-exporting
5. `python3 CMEF/...` → Script can now access all required variables

### Step 5: Monitor Progress

```bash
# Watch log in real-time
tail -f CMEF/logs/auto_unified_setup.log
```

**Expected Timeline:**
- Schema creation: ~2 seconds
- CMEF import (4,497 companies): ~8-10 minutes
- MEDICA import (1,321 companies): ~3-5 minutes
- **Total**: ~15 minutes

**Expected Output:**
```
======================================================================
STEP 1: CREATING SCHEMA
======================================================================
✅ Table created
📑 Creating indexes...
✅ Created 5 indexes

======================================================================
STEP 2: IMPORTING CMEF DATA
======================================================================
📖 Loading: .../enriched_companies.json
✅ Loaded 4497 CMEF companies
💾 Inserting CMEF companies...
  Progress: 500/4497 (493 inserted, 7 skipped)
  Progress: 1000/4497 (988 inserted, 12 skipped)
  ...
✅ Imported 4477 CMEF companies (20 skipped - no name)

======================================================================
STEP 3: IMPORTING MEDICA DATA
======================================================================
📖 Loading: .../china_exhibitors_enriched.json
✅ Loaded 1321 MEDICA companies
💾 Inserting MEDICA companies...
  Progress: 500/1321 (500 inserted, 0 skipped)
  ...
✅ Imported 1321 MEDICA companies (0 skipped - no name)

======================================================================
DATABASE SUMMARY
======================================================================

📊 By Data Source:
  CMEF: 4477 companies (4477 classified, 100.0%)
  MEDICA: 1321 companies (588 classified, 44.5%)

📈 TOTAL: 5798 companies

📂 Top 10 Categories:
  Other Medical Equipment: 1589 (MEDICA: 733, CMEF: 856)
  Disposable Medical Supplies: 423 (MEDICA: 119, CMEF: 304)
  ...

✅ SETUP COMPLETED SUCCESSFULLY!
```

## 🔧 Script Files Created

### 1. `auto_setup_unified_db.py`
**Location**: `/Users/gabrielreginatto/Desktop/Code/Medical/CMEF/auto_setup_unified_db.py`

**Purpose**: Fully automated database setup

**What It Does:**
1. Creates `medical_exhibitors` table with unified schema
2. Creates 5 indexes (including GIN index for keyword arrays)
3. Imports CMEF enriched data (4,497 companies)
4. Imports MEDICA enriched data (1,321 companies)
5. Prints summary statistics

**Key Features:**
- ✅ Handles NULL values (skips companies without names)
- ✅ Uses transactions for atomicity
- ✅ Shows progress every 500 companies
- ✅ Handles ON CONFLICT (prevents duplicates)
- ✅ Works with existing database infrastructure

### 2. `create_unified_database.sql`
**Location**: `/Users/gabrielreginatto/Desktop/Code/Medical/CMEF/create_unified_database.sql`

**Purpose**: Standalone SQL schema (if you prefer SQL over Python)

**Usage** (if using psql directly):
```bash
# NOT RECOMMENDED - requires psql client
# Use Python script instead
gcloud sql connect pncp-medical-db \
  --user=gabrielreginatto@gmail.com \
  --database=medical_exhibitors < create_unified_database.sql
```

## 📊 Unified Schema

### Table: `medical_exhibitors`

```sql
CREATE TABLE medical_exhibitors (
    -- Identity
    id SERIAL PRIMARY KEY,
    name VARCHAR(500) NOT NULL,              -- Company name
    company_name_zh VARCHAR(500),             -- Chinese name (CMEF)

    -- Location
    location VARCHAR(200),                    -- Hall/city
    booth_number VARCHAR(50),                 -- Booth number
    address TEXT,
    country VARCHAR(100),
    region VARCHAR(50),

    -- Contact
    email VARCHAR(255),
    phone VARCHAR(100),
    website VARCHAR(500),

    -- Event Tracking
    event VARCHAR(100) NOT NULL,              -- "MEDICA 2025" or "CMEF 2025"
    data_source VARCHAR(50) NOT NULL,         -- "MEDICA" or "CMEF" ⭐

    -- Descriptions
    company_description TEXT,
    raw_text TEXT,

    -- AI Classification ⭐
    product_category VARCHAR(200),
    product_keywords TEXT[],                  -- Array for GIN indexing
    category_confidence FLOAT,

    -- Website Validation
    website_validated BOOLEAN DEFAULT FALSE,
    website_status_code INTEGER,

    -- Timestamps
    scraped_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    CONSTRAINT unique_company_event UNIQUE(name, event)
);
```

### Indexes Created

```sql
-- Basic indexes
CREATE INDEX idx_exhibitors_name ON medical_exhibitors(name);
CREATE INDEX idx_exhibitors_data_source ON medical_exhibitors(data_source);
CREATE INDEX idx_exhibitors_category ON medical_exhibitors(product_category);
CREATE INDEX idx_exhibitors_booth ON medical_exhibitors(booth_number);

-- GIN index for array keyword search
CREATE INDEX idx_exhibitors_keywords ON medical_exhibitors USING GIN(product_keywords);
```

## 🔍 Verification Queries

### After Import, Run These Queries:

```sql
-- 1. Check total count
SELECT COUNT(*) FROM medical_exhibitors;
-- Expected: ~5,798

-- 2. Count by source
SELECT data_source, COUNT(*)
FROM medical_exhibitors
GROUP BY data_source;
-- Expected: CMEF: 4477, MEDICA: 1321

-- 3. Test keyword search
SELECT name, product_category
FROM medical_exhibitors
WHERE 'ultrasound' = ANY(product_keywords)
LIMIT 10;
-- Should return companies from both sources

-- 4. Check classification rate
SELECT
    data_source,
    COUNT(*) as total,
    COUNT(product_category) as classified,
    ROUND(COUNT(product_category)::numeric / COUNT(*) * 100, 1) as pct
FROM medical_exhibitors
GROUP BY data_source;
-- Expected: CMEF 100%, MEDICA 44.5%

-- 5. Top categories
SELECT product_category, COUNT(*) as count
FROM medical_exhibitors
WHERE product_category IS NOT NULL
GROUP BY product_category
ORDER BY count DESC
LIMIT 10;
```

## 🚨 Troubleshooting

### Issue: "File pncp-key.json was not found"
**Solution:**
```bash
# Check file exists
ls -la /Users/gabrielreginatto/Desktop/Code/Medical/config/pncp-key.json

# Set correct path
export GOOGLE_APPLICATION_CREDENTIALS="/Users/gabrielreginatto/Desktop/Code/Medical/config/pncp-key.json"
```

### Issue: "Missing required environment variables"
**Solution:**
```bash
# Must run from parent directory
cd /Users/gabrielreginatto/Desktop/Code/Medical

# Load .env file
set -a && source .env && set +a

# Verify variables loaded
echo $GOOGLE_CLOUD_PROJECT  # Should show: medical-473219
echo $CLOUD_SQL_INSTANCE    # Should show: pncp-medical-db
```

### Issue: "null value in column 'name' violates not-null constraint"
**Solution:** Already handled in script - skips companies without names

```python
# Script already includes this check
if not company.get('company_name_en'):  # or company.get('name')
    skipped += 1
    continue
```

### Issue: Script takes too long / times out
**Solution:** Run in background

```bash
# Run in background
nohup bash -c "set -a && source .env && export GOOGLE_APPLICATION_CREDENTIALS='/Users/gabrielreginatto/Desktop/Code/Medical/config/pncp-key.json' && set +a && python3 CMEF/auto_setup_unified_db.py" > CMEF/logs/auto_unified_setup_bg.log 2>&1 &

# Monitor progress
tail -f CMEF/logs/auto_unified_setup_bg.log
```

### Issue: "Unclosed client session" warning
**Solution:** Harmless warning - database import still succeeds. Related to Cloud SQL Connector cleanup.

## 📝 Environment Variables Required

From `.env` file:
```bash
GOOGLE_CLOUD_PROJECT=medical-473219
CLOUD_SQL_REGION=us-central1
CLOUD_SQL_INSTANCE=pncp-medical-db
DATABASE_NAME=pncp_medical_data  # This gets overridden to medical_exhibitors
```

Additional:
```bash
GOOGLE_APPLICATION_CREDENTIALS=/Users/gabrielreginatto/Desktop/Code/Medical/config/pncp-key.json
```

## 🎉 Success Indicators

✅ Schema created without errors
✅ ~4,477 CMEF companies imported (20 skipped)
✅ ~1,321 MEDICA companies imported (0 skipped)
✅ Total ~5,798 companies in database
✅ GIN indexes created for fast keyword search
✅ Summary statistics displayed

## 📚 Related Documentation

- **MEDICA Enrichment**: `MEDICA_ENRICHMENT_GUIDE.md`
- **Migration Guide**: `MIGRATION_GUIDE.md` (old approach - modifies existing DB)
- **Unified Database README**: `README_UNIFIED_DATABASE.md`

## 🔄 To Repeat This Process

```bash
# 1. Navigate to project root
cd /Users/gabrielreginatto/Desktop/Code/Medical

# 2. Create new database (change name as needed)
gcloud sql databases create my_new_database \
  --instance=pncp-medical-db \
  --project=medical-473219

# 3. Run automated setup
set -a && \
source .env && \
export GOOGLE_APPLICATION_CREDENTIALS="/Users/gabrielreginatto/Desktop/Code/Medical/config/pncp-key.json" && \
set +a && \
python3 CMEF/auto_setup_unified_db.py

# Done! No manual SQL required.
```

## ⏱️ Expected Timeline

| Step | Duration |
|------|----------|
| Database creation (gcloud) | ~10 seconds |
| Schema creation | ~2 seconds |
| CMEF import (4,497 companies) | ~10 minutes |
| MEDICA import (1,321 companies) | ~3 minutes |
| **TOTAL** | **~15 minutes** |

---

**Last Updated**: 2025-11-23
**Database**: `medical_exhibitors`
**Instance**: `pncp-medical-db`
**Total Companies**: ~5,798 (CMEF: 4,477, MEDICA: 1,321)
**Classification**: 100% CMEF, 44.5% MEDICA
