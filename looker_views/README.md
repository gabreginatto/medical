# Unified Medical Exhibitors Looker Views

This directory contains the unified Looker views for the combined CMEF + MEDICA exhibitor database.

## 📊 Database Overview

- **Database**: `medical_exhibitors` on Cloud SQL `pncp-medical-db`
- **Total Companies**: 5,638 unique (5,717 original - 79 duplicates)
- **CMEF**: 4,396 companies
- **MEDICA**: 1,242 unique companies
- **International**: 79 companies exhibiting at both events

## 📁 Views & Models

### Main Views

1. **`medical_exhibitors.view.lkml`**
   - Uses `medical_exhibitors_unique` (deduplicated view)
   - Contains all company fields including:
     - Basic info (name, Chinese name, contact, location)
     - AI classification (product_category, keywords, confidence)
     - Website validation status
     - Data completeness scoring
   - **5,638 unique companies**

2. **`international_exhibitors.view.lkml`**
   - Uses `medical_exhibitors_merged_duplicates` view
   - Special view for companies at both CMEF & MEDICA
   - Combines booth info from both events
   - **79 international companies**

3. **`medica_product_images.view.lkml`**
   - Product catalog images (MEDICA data only)
   - Includes inline image display, galleries, thumbnails
   - Joins to exhibitors via `exhibitor_id`

4. **`medica_documents.view.lkml`**
   - PDF brochures and documents (MEDICA data only)
   - Includes download links and file size info
   - Joins to exhibitors via `exhibitor_id`

### Model File

**`medical_exhibitors.model.lkml`**

Defines 6 explores:

1. **Medical Exhibitors (All)** - Main explore with all 5,638 unique companies
2. **CMEF Exhibitors** - Filtered to CMEF only (4,396 companies)
3. **MEDICA Exhibitors** - Filtered to MEDICA only (1,242 companies)
4. **International Exhibitors** - Companies at both events (79 companies)
5. **China Exhibitors (MEDICA)** - Chinese companies at MEDICA
6. **Product Categories** - Analysis by AI-classified categories

## 🎯 Key Features

### AI Classification
All 5,717 companies (100%) are AI-classified using Gemini 2.5 Flash with:
- `product_category` - One of 50+ medical equipment categories
- `product_keywords` - Array of relevant product terms
- `category_confidence` - Confidence score (0-1)

### Top Product Categories
1. Other Medical Equipment (1,973)
2. Disposable Medical Supplies (908)
3. Orthopedics & Rehabilitation (543)
4. Laboratory & Diagnostics (525)
5. Surgical Instruments & Tools (404)

### Data Completeness Scoring
The `completeness_score` dimension scores each company (0-7) based on:
- Chinese name, email, phone, website, address, description, booth number

### Deduplication
- Original setup had 79 duplicate companies (same company at both events)
- `medical_exhibitors_unique` view automatically excludes duplicates
- `international_exhibitors` view specifically shows the 79 companies at both events

## 🔍 Example Queries

### All Exhibitors
```sql
SELECT * FROM medical_exhibitors_unique LIMIT 10;
```

### CMEF Only
```sql
SELECT * FROM medical_exhibitors_unique WHERE data_source = 'CMEF';
```

### MEDICA Only
```sql
SELECT * FROM medical_exhibitors_unique WHERE data_source = 'MEDICA';
```

### International Companies
```sql
SELECT * FROM medical_exhibitors_merged_duplicates;
```

### By Product Category
```sql
SELECT product_category, COUNT(*) as count
FROM medical_exhibitors_unique
WHERE product_category IS NOT NULL
GROUP BY product_category
ORDER BY count DESC;
```

### Companies with Contact Info
```sql
SELECT name, email, phone, website
FROM medical_exhibitors_unique
WHERE email IS NOT NULL OR phone IS NOT NULL
ORDER BY completeness_score DESC;
```

## 📈 Looker Dashboard Ideas

1. **Executive Overview**
   - Total companies by data source
   - Geographic distribution (map)
   - Top product categories
   - Data completeness metrics

2. **International Companies**
   - Companies exhibiting at both events
   - Booth locations comparison
   - Contact information

3. **Product Category Deep Dive**
   - Distribution across CMEF vs MEDICA
   - Category-specific contact lists
   - Keyword analysis

4. **Data Quality**
   - Completeness scoring
   - Website validation status
   - Missing field analysis

5. **MEDICA Product Catalogs**
   - Product images gallery
   - Documents and brochures
   - Filter by category

## 🔗 Database Tables Reference

- `medical_exhibitors` - Original data (all 5,717 records)
- `medical_exhibitors_unique` - Deduplicated view (5,638 records) ✅ **Use this**
- `medical_exhibitors_merged_duplicates` - International companies (79 records)
- `exhibitor_dedup_map` - Deduplication mapping table
- `medica_product_images` - Product images (MEDICA only)
- `medica_documents` - PDF documents (MEDICA only)

## 💡 Migration from Old Views

### Old MEDICA Setup
- `medica_exhibitors` → Now `medical_exhibitors` (filtered to MEDICA)
- Three explores (all, China, Global) → Now 6 explores with better filtering

### Key Changes
1. Uses deduplicated `medical_exhibitors_unique` view by default
2. Added `data_source` dimension to filter CMEF vs MEDICA
3. Added AI classification fields (category, keywords, confidence)
4. Added international exhibitors view
5. Added completeness scoring
6. Product images and documents still work the same way (MEDICA only)

## 🚀 Next Steps

1. Import these views into your Looker project
2. Update connection name if different from `medical_cloud_sql`
3. Create dashboards using the explores
4. Set up scheduled reports for stakeholders
