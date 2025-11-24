# Looker Views Migration Guide

## 🔄 Old vs New Structure

### Old MEDICA Setup (`Medica/looker_views/`)

**4 files:**
1. `medica_exhibitors.view.lkml` - MEDICA data only
2. `medica_product_images.view.lkml` - Product images
3. `medica_documents.view.lkml` - PDF documents
4. `medica.model.lkml` - 3 explores (All, China, Global)

**Limitations:**
- MEDICA data only (1,321 companies)
- No CMEF data
- No AI classification
- No deduplication
- Limited filtering options

### New Unified Setup (`looker_views/`)

**6 files:**
1. `medical_exhibitors.view.lkml` - **Unified CMEF + MEDICA (5,638 unique)**
2. `international_exhibitors.view.lkml` - **Companies at both events (79)**
3. `medica_product_images.view.lkml` - Product images (same)
4. `medica_documents.view.lkml` - PDF documents (same)
5. `medical_exhibitors.model.lkml` - **6 explores** (All, CMEF, MEDICA, International, China, Categories)
6. `README.md` - Comprehensive documentation

**Improvements:**
✅ Combined CMEF + MEDICA data (5,638 unique companies)
✅ AI classification on 100% of companies (Gemini 2.5 Flash)
✅ Automatic deduplication (79 duplicates identified)
✅ International companies view (both events)
✅ Data completeness scoring
✅ Website validation status
✅ Better filtering and segmentation
✅ Product category analysis

## 📊 Data Comparison

| Metric | Old (MEDICA only) | New (Unified) |
|--------|-------------------|---------------|
| Total Companies | 1,321 | 5,638 unique |
| CMEF Companies | 0 | 4,396 |
| MEDICA Companies | 1,321 | 1,242 (deduplicated) |
| Duplicates | Unknown | 79 identified |
| AI Classification | None | 100% classified |
| Product Categories | None | 50+ categories |
| Chinese Names | Limited | Full (CMEF data) |

## 🎯 Explore Mapping

### Old Explores → New Explores

| Old Explore | New Equivalent | Notes |
|-------------|----------------|-------|
| `medica_exhibitors` | `medical_exhibitors` (filtered to MEDICA) | Now includes AI classification |
| `china_exhibitors` | `china_exhibitors` | Same filter, more data |
| `global_exhibitors` | `medical_exhibitors` (filter: `data_source = MEDICA` AND `country != China`) | Manual filter needed |
| N/A | **`cmef_exhibitors`** | ✨ **NEW**: CMEF companies only |
| N/A | **`international_exhibitors`** | ✨ **NEW**: Both events |
| N/A | **`product_categories`** | ✨ **NEW**: Category analysis |

## 🔑 Key Dimension Changes

### Renamed/Updated Dimensions

| Old | New | Change |
|-----|-----|--------|
| `location` | `location` | Same for MEDICA, `booth_number` for CMEF |
| N/A | **`data_source`** | ✨ **NEW**: "CMEF" or "MEDICA" |
| N/A | **`company_name_zh`** | ✨ **NEW**: Chinese company name |
| N/A | **`product_category`** | ✨ **NEW**: AI-classified category |
| N/A | **`product_keywords`** | ✨ **NEW**: AI-extracted keywords |
| N/A | **`category_confidence`** | ✨ **NEW**: AI confidence score |
| N/A | **`completeness_score`** | ✨ **NEW**: Data completeness (0-7) |
| N/A | **`website_validated`** | ✨ **NEW**: Website validation status |

### Same Dimensions (No Changes)

- `name`, `email`, `phone`, `website`, `address`
- `country`, `region`, `event`
- `company_description`
- Time dimensions: `scraped_at`, `created_at`, `updated_at`

## 📈 New Measures

Added measures in unified view:

- `count_cmef` - Count of CMEF exhibitors
- `count_medica` - Count of MEDICA exhibitors
- `count_classified` - Companies with AI classification
- `avg_completeness_score` - Average data completeness
- `avg_confidence` - Average classification confidence

## 🚀 Migration Steps

1. **Backup old views** (already in `Medica/looker_views/`)

2. **Import new views to Looker:**
   ```
   /looker_views/
   ├── medical_exhibitors.view.lkml
   ├── international_exhibitors.view.lkml
   ├── medica_product_images.view.lkml
   ├── medica_documents.view.lkml
   └── medical_exhibitors.model.lkml
   ```

3. **Update database connection:**
   - Database: `medical_exhibitors` (new unified database)
   - Instance: `pncp-medical-db` (same)
   - Connection name in model: `medical_cloud_sql`

4. **Update existing dashboards:**
   - Change explore from `medica_exhibitors` to `medical_exhibitors`
   - Add `data_source` filter to maintain MEDICA-only filtering if needed
   - Optional: Add product category filters

5. **Create new dashboards:**
   - CMEF exhibitors dashboard
   - International companies comparison
   - Product category analysis
   - Data completeness report

## 📋 Example Dashboard Conversions

### Old MEDICA Dashboard

```lookml
- explore: medica_exhibitors
  dimensions: [name, location, country]
  measures: [count]
```

### New Equivalent (MEDICA only)

```lookml
- explore: medical_exhibitors
  dimensions: [name, location, country, data_source]
  measures: [count_medica]
  filters:
    data_source: MEDICA
```

### New Enhanced (All Data)

```lookml
- explore: medical_exhibitors
  dimensions: [name, location, country, data_source, product_category]
  measures: [count, count_cmef, count_medica, count_classified]
  # No filters - shows all data
```

## 💡 Pro Tips

1. **Use `medical_exhibitors_unique` by default** - Already deduplicated
2. **Filter by `data_source`** - "CMEF" or "MEDICA" for event-specific views
3. **Use `international_exhibitors`** - For companies at both events
4. **Leverage `product_category`** - 100% of companies are classified
5. **Check `completeness_score`** - Find companies with most complete data
6. **MEDICA images/docs still work** - Join conditions filter automatically

## ⚠️ Breaking Changes

1. **Database name changed:**
   - Old: `medica` database
   - New: `medical_exhibitors` database

2. **Table name changed:**
   - Old: `medica_exhibitors` table
   - New: `medical_exhibitors_unique` view (deduplicated)

3. **Company count changed (MEDICA):**
   - Old: 1,321 companies
   - New: 1,242 unique companies (79 duplicates removed)

4. **Product images/documents join:**
   - Now requires `data_source = 'MEDICA'` condition
   - Already handled in model file

## ✅ Validation Queries

After migration, run these queries to verify:

```sql
-- Should return 5638
SELECT COUNT(*) FROM medical_exhibitors_unique;

-- Should return 4396
SELECT COUNT(*) FROM medical_exhibitors_unique WHERE data_source = 'CMEF';

-- Should return 1242
SELECT COUNT(*) FROM medical_exhibitors_unique WHERE data_source = 'MEDICA';

-- Should return 79
SELECT COUNT(*) FROM medical_exhibitors_merged_duplicates;

-- Should return 5717 (100%)
SELECT COUNT(*) FROM medical_exhibitors_unique WHERE product_category IS NOT NULL;
```

## 📞 Support

For questions about the new views:
1. Check `README.md` in `/looker_views/`
2. Review database schema in `/CMEF/CLAUDE.md`
3. Check deduplication logic in `/CMEF/create_deduplicated_view.py`
