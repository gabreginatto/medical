# Unified Medical Exhibitors Database

## 🎯 Overview

This project creates a **unified database** combining MEDICA and CMEF medical equipment exhibitor catalogs with AI-powered product categorization.

**Key Features:**
- ✅ Single database for both MEDICA and CMEF companies
- ✅ AI classification of products using Gemini 2.5 Flash
- ✅ Searchable product keywords
- ✅ Source tracking (MEDICA vs CMEF)
- ✅ Safe migration (original database untouched)

## 📊 Database Stats

| Metric | Count |
|--------|-------|
| **Total Companies** | ~5,818 |
| MEDICA Companies | ~1,321 |
| CMEF Companies | ~4,497 |
| Classification Rate | 99.9% |
| Product Categories | 15+ |

## 🚀 Quick Start

### Option 1: Automated Migration (Recommended)

```bash
cd /Users/gabrielreginatto/Desktop/Code/Medical/CMEF

# Run complete migration pipeline
./run_full_migration.sh
```

This will:
1. Create new `medical_unified` database schema
2. Migrate MEDICA data (read-only from source)
3. Import CMEF data
4. Classify all companies with AI

**Time:** ~5-10 minutes total

### Option 2: Manual Step-by-Step

See [MIGRATION_GUIDE.md](./MIGRATION_GUIDE.md) for detailed instructions.

## 📁 Files

### Migration Scripts
- `create_unified_database.sql` - Database schema
- `migrate_medica_to_unified.py` - MEDICA data migration
- `import_cmef_to_unified.py` - CMEF data import
- `classify_unified_companies.py` - AI classification
- `run_full_migration.sh` - Automated pipeline

### Documentation
- `MIGRATION_GUIDE.md` - Detailed migration guide
- `README_UNIFIED_DATABASE.md` - This file

### Legacy Scripts (Original Approach)
- `classify_medica_companies.py` - Old approach (modifies existing DB)
- `import_cmef_to_medica.py` - Old approach (modifies existing DB)
- `migrate_unified_schema.sql` - Old approach (modifies existing DB)

⚠️ **DO NOT USE LEGACY SCRIPTS** - They modify the existing database

## 🗄️ Database Schema

### Table: `medical_exhibitors`

```sql
CREATE TABLE medical_exhibitors (
    -- Identity
    id SERIAL PRIMARY KEY,
    name VARCHAR(500) NOT NULL,              -- English name
    company_name_zh VARCHAR(500),             -- Chinese name (CMEF)

    -- Location
    location VARCHAR(200),                    -- Hall location
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
    company_description TEXT,                 -- Full description
    raw_text TEXT,                            -- Raw OCR text (MEDICA only)

    -- AI Classification (NEW) ⭐
    product_category VARCHAR(200),            -- e.g., "Diagnostic Equipment"
    product_keywords TEXT[],                  -- Array of keywords
    category_confidence FLOAT,                -- 0.0 - 1.0

    -- Website Validation (NEW) ⭐
    website_validated BOOLEAN,
    website_status_code INTEGER,

    -- Timestamps
    scraped_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    CONSTRAINT unique_company_event UNIQUE(name, event)
);
```

### Key Indexes

- **GIN Index** on `product_keywords` for fast array search
- **Full-text Index** on `company_description`
- **B-tree Indexes** on `product_category`, `data_source`, `country`, `event`

### Views

- `medica_exhibitors` - MEDICA companies only (backward compatibility)
- `cmef_exhibitors` - CMEF companies only

## 🔍 Example Queries

### Search by Product Keyword
```sql
SELECT name, data_source, product_category, website
FROM medical_exhibitors
WHERE 'ultrasound' = ANY(product_keywords)
ORDER BY category_confidence DESC;
```

### Compare MEDICA vs CMEF
```sql
SELECT
    product_category,
    COUNT(*) FILTER (WHERE data_source = 'MEDICA') as medica,
    COUNT(*) FILTER (WHERE data_source = 'CMEF') as cmef
FROM medical_exhibitors
WHERE product_category IS NOT NULL
GROUP BY product_category
ORDER BY (medica + cmef) DESC;
```

### Full-Text Search
```sql
SELECT name, data_source, product_category
FROM medical_exhibitors
WHERE to_tsvector('english', company_description)
    @@ to_tsquery('english', 'surgical & robotic')
ORDER BY category_confidence DESC;
```

### Chinese Companies
```sql
SELECT name, company_name_zh, booth_number, product_category
FROM medical_exhibitors
WHERE company_name_zh IS NOT NULL
LIMIT 10;
```

## 📈 Product Categories

The AI classifier recognizes 15+ medical equipment categories:

- Diagnostic Equipment (imaging, monitoring)
- Surgical Instruments (tools, robotics)
- Orthopedics & Rehabilitation (wheelchairs, prosthetics)
- Laboratory Equipment (analyzers, microscopes)
- Patient Monitoring Systems
- Medical Furniture (beds, tables)
- Disposable Medical Supplies
- Sterilization Equipment
- Emergency & Intensive Care
- Ophthalmic Equipment
- Dental Equipment
- Physiotherapy Equipment
- Medical Imaging (X-ray, MRI, ultrasound)
- Hospital IT Systems
- Other Medical Equipment

## 🔐 Safety Features

✅ **Non-Destructive**: Original `medical` database is NEVER modified
✅ **Read-Only Migration**: MEDICA migration only reads from source
✅ **Easy Rollback**: Simply drop `medical_unified` if needed
✅ **Verification**: Built-in checks at each step
✅ **Logging**: Complete logs in `logs/` directory

## 🎨 Looker Integration

### Update Connection

1. Go to Looker Studio
2. Data Sources → Edit connection
3. Update database: `medical` → `medical_unified`
4. Test connection

### New Dimensions

```lookml
dimension: data_source {
  type: string
  sql: ${TABLE}.data_source ;;
}

dimension: product_category {
  type: string
  sql: ${TABLE}.product_category ;;
}

dimension: product_keywords_list {
  type: string
  sql: ARRAY_TO_STRING(${TABLE}.product_keywords, ', ') ;;
}

dimension: category_confidence {
  type: number
  sql: ${TABLE}.category_confidence ;;
  value_format: "0.0%"
}
```

### Dashboard Ideas

1. **Overview Dashboard**
   - Total companies by source (MEDICA vs CMEF)
   - Classification rate
   - Top 10 categories

2. **Category Analysis**
   - Breakdown by product category
   - MEDICA vs CMEF comparison
   - Confidence distribution

3. **Geographic View**
   - Companies by country
   - Interactive map
   - Regional trends

4. **Product Search**
   - Keyword search input
   - Results table with filters
   - Export functionality

## 📝 Logs

All operations are logged to:

```
logs/
├── schema_creation.log        # Database schema creation
├── medica_migration.log        # MEDICA data migration
├── cmef_unified_import.log     # CMEF data import
└── unified_classification.log  # AI classification
```

## 🔄 Rollback Instructions

If you need to rollback:

```bash
# Option 1: Drop new database
dropdb medical_unified

# Option 2: Drop table only
psql -d medical_unified -c "DROP TABLE medical_exhibitors CASCADE;"

# Option 3: Keep new database, revert Looker
# Just update Looker connection back to 'medical' database
```

**Important**: Original `medical` database is untouched and can be used anytime.

## ⚙️ Configuration

### Environment Variables

```bash
# Source database (old 'medical' database)
export SOURCE_DB_URL="postgresql://user:password@host:5432/medical"

# Target database (new 'medical_unified' database)
export TARGET_DB_URL="postgresql://user:password@host:5432/medical_unified"
export UNIFIED_DB_URL="$TARGET_DB_URL"
```

### Gemini AI Settings

Model: `gemini-2.5-flash` (configured in `config.py`)

## 🆘 Troubleshooting

### Issue: Schema creation fails
```bash
# Check if database exists
psql -l | grep medical_unified

# If not, create it:
createdb medical_unified
```

### Issue: Migration script hangs
```bash
# Check database connectivity
psql -h <host> -U postgres -d medical_unified -c "SELECT 1;"
```

### Issue: Classification is slow
This is normal. Gemini processes ~10 companies/second.
- 1,321 MEDICA companies ≈ 2-3 minutes

### Issue: Some companies not classified
Expected. Companies without descriptions cannot be classified (~6 companies).

## 📞 Support

For issues:
1. Check logs in `logs/` directory
2. Review [MIGRATION_GUIDE.md](./MIGRATION_GUIDE.md)
3. Verify database connection
4. Check Gemini API quota

## 🎉 Success Criteria

After successful migration:

- ✅ ~5,818 total companies in database
- ✅ ~1,321 MEDICA companies with `data_source='MEDICA'`
- ✅ ~4,497 CMEF companies with `data_source='CMEF'`
- ✅ ~99.9% classification rate
- ✅ Product keywords searchable
- ✅ Original database untouched

## 📚 Additional Resources

- [MIGRATION_GUIDE.md](./MIGRATION_GUIDE.md) - Detailed step-by-step guide
- [CMEF Processing Pipeline](./README.md) - Original CMEF extraction docs
- Looker Views: `/Users/gabrielreginatto/Desktop/Code/Medical/Medica/looker_views/`

---

**Last Updated**: 2025-11-23
**Version**: 1.0
**Status**: Ready for production
