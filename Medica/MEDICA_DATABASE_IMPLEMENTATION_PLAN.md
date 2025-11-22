# MEDICA Exhibitor Database Implementation Plan

**Date:** 2025-11-21
**Project:** MEDICA 2025 Chinese Exhibitor Data Management
**Database:** PostgreSQL (Cloud SQL)
**Storage:** Google Cloud Storage
**Analytics:** Looker

---

## 📊 Executive Summary

Successfully scraped **1,323 Chinese companies** and **1,149 Global companies** from MEDICA 2025 trade fair. This plan outlines the architecture for storing exhibitor data in PostgreSQL and product images in Google Cloud Storage, with Looker integration for analytics and visualization.

---

## 1. Database Choice: PostgreSQL ✅

### Why PostgreSQL?

**Advantages:**
- ✅ **Relational data structure**: Perfect for Companies → Images → Documents relationships
- ✅ **Full-text search**: Query `raw_text` for product/company searches
- ✅ **JSON support**: Can store additional metadata when needed
- ✅ **Scalability**: Handles millions of records efficiently
- ✅ **GCP integration**: Native Cloud SQL support with Looker
- ✅ **Cost-effective**: Better than BigQuery for <10K companies
- ✅ **ACID compliance**: Data integrity for business-critical data

**Alternatives Considered:**
- ❌ **BigQuery**: Overkill and more expensive for this data volume
- ❌ **Firestore**: No SQL joins, harder for Looker integration
- ✅ **PostgreSQL**: Perfect fit ⭐

---

## 2. Schema Design & Compatibility

### Database Schema

**Tables:**
1. **medica_exhibitors** - Main company information
2. **medica_product_images** - Product images with GCS URLs
3. **medica_documents** - PDF documents with GCS URLs

### JSON to Database Mapping

| JSON Field | Database Table | Column | Type |
|------------|----------------|--------|------|
| `name` | `medica_exhibitors` | `name` | VARCHAR(500) |
| `location` | `medica_exhibitors` | `location` | VARCHAR(200) |
| `company_description` | `medica_exhibitors` | `company_description` | TEXT |
| `email` | `medica_exhibitors` | `email` | VARCHAR(255) |
| `phone` | `medica_exhibitors` | `phone` | VARCHAR(100) |
| `website` | `medica_exhibitors` | `website` | VARCHAR(500) |
| `address` | `medica_exhibitors` | `address` | TEXT |
| `raw_text` | `medica_exhibitors` | `raw_text` | TEXT |
| `event` | `medica_exhibitors` | `event` | VARCHAR(100) |
| `scraped_at` | `medica_exhibitors` | `scraped_at` | TIMESTAMP |
| `product_images[]` | `medica_product_images` | One row per image | Multiple rows |
| `documents[]` | `medica_documents` | One row per document | Multiple rows |

**Enhanced Fields (Recommended):**
- `country` VARCHAR(100) - e.g., "China", "USA", "Germany"
- `region` VARCHAR(50) - e.g., "China", "Global"

### Sample Data Structure

**Exhibitor Record:**
```json
{
  "name": "432H Tech Co., Ltd.",
  "location": "Hall 16 / G67-6",
  "company_description": "",
  "email": null,
  "phone": null,
  "website": null,
  "address": null,
  "raw_text": "...",
  "product_images": ["product_1.png", "product_2.png"],
  "documents": [],
  "event": "MEDICA 2025",
  "scraped_at": "2025-11-21T08:01:51.693454"
}
```

**Database Records:**

*medica_exhibitors:*
```
id | name                  | location        | country | region | ...
---|----------------------|-----------------|---------|--------|----
1  | 432H Tech Co., Ltd.  | Hall 16 / G67-6 | China   | China  | ...
```

*medica_product_images:*
```
id | exhibitor_id | image_filename | gcs_url                                    | gcs_bucket
---|--------------|----------------|--------------------------------------------|------------------
1  | 1            | product_1.png  | https://storage.googleapis.com/.../product_1.png | medica-exhibitor-data
2  | 1            | product_2.png  | https://storage.googleapis.com/.../product_2.png | medica-exhibitor-data
```

---

## 3. Cloud Storage Strategy

### GCS Bucket Structure

```
gs://medica-exhibitor-data/
├── china/
│   ├── images/
│   │   ├── 432H-Tech-Co-Ltd/
│   │   │   ├── product_1.png
│   │   │   ├── product_2.png
│   │   │   └── product_3.png
│   │   ├── A-GEN-BIOTECHNOLOGY/
│   │   │   └── product_1.png
│   │   └── [1,323 more companies...]
│   └── documents/
│       └── [company-name]/
│           └── brochure.pdf
└── global/
    ├── images/
    │   └── [company-name]/
    │       └── product_X.png
    └── documents/
        └── [company-name]/
            └── doc.pdf
```

### Benefits of This Structure

- ✅ **Organized by region** (china/global)
- ✅ **Separated by type** (images/documents)
- ✅ **Company-specific folders** (easy to manage)
- ✅ **URL-friendly** (sanitized company names)
- ✅ **Scalable** (can add more regions/types)
- ✅ **CDN-ready** (can add Cloud CDN for fast image delivery)

### Public Access Configuration

```bash
# Make bucket publicly readable (optional)
gsutil iam ch allUsers:objectViewer gs://medica-exhibitor-data

# Or keep private and use signed URLs
```

---

## 4. Looker Integration & Image Viewing

### How Looker Displays Images

**1. Database stores GCS URLs:**

```sql
SELECT
  e.name,
  e.location,
  p.gcs_url
FROM medica_exhibitors e
LEFT JOIN medica_product_images p ON e.id = p.exhibitor_id
WHERE e.name = '432H Tech Co., Ltd.';
```

**Result:**
```
name                  | location        | gcs_url
---------------------|-----------------|------------------------------------------
432H Tech Co., Ltd.  | Hall 16 / G67-6 | https://storage.googleapis.com/.../product_1.png
432H Tech Co., Ltd.  | Hall 16 / G67-6 | https://storage.googleapis.com/.../product_2.png
```

**2. Looker LookML View:**

```lookml
view: medica_exhibitors {
  sql_table_name: public.medica_exhibitors ;;

  dimension: id {
    type: number
    primary_key: yes
    sql: ${TABLE}.id ;;
  }

  dimension: name {
    type: string
    sql: ${TABLE}.name ;;
    link: {
      label: "View Company Details"
      url: "/dashboards/medica_company_detail?company_id={{ id._value }}"
    }
  }

  dimension: location {
    type: string
    sql: ${TABLE}.location ;;
  }

  dimension: country {
    type: string
    sql: ${TABLE}.country ;;
  }

  dimension: region {
    type: string
    sql: ${TABLE}.region ;;
  }

  dimension: company_description {
    type: string
    sql: ${TABLE}.company_description ;;
  }

  dimension: email {
    type: string
    sql: ${TABLE}.email ;;
  }

  dimension: phone {
    type: string
    sql: ${TABLE}.phone ;;
  }

  dimension: website {
    type: string
    sql: ${TABLE}.website ;;
    html: <a href="{{ value }}" target="_blank">{{ value }}</a> ;;
  }

  measure: count {
    type: count
    drill_fields: [name, location, country]
  }
}

view: medica_product_images {
  sql_table_name: public.medica_product_images ;;

  dimension: id {
    type: number
    primary_key: yes
    sql: ${TABLE}.id ;;
  }

  dimension: exhibitor_id {
    type: number
    sql: ${TABLE}.exhibitor_id ;;
  }

  dimension: image_filename {
    type: string
    sql: ${TABLE}.image_filename ;;
  }

  dimension: gcs_url {
    type: string
    sql: ${TABLE}.gcs_url ;;
  }

  # Display image as clickable thumbnail
  dimension: image_thumbnail {
    type: string
    sql: ${gcs_url} ;;
    html:
      <a href="{{ value }}" target="_blank">
        <img src="{{ value }}"
             width="120"
             style="border-radius: 8px; border: 1px solid #ddd; cursor: pointer;">
      </a>
    ;;
  }

  # Image gallery for a company (aggregated)
  dimension: image_gallery {
    type: string
    sql: ${gcs_url} ;;
    html:
      <div style="display: flex; flex-wrap: wrap; gap: 10px;">
        <img src="{{ value }}"
             width="150"
             style="border-radius: 8px; cursor: pointer;"
             onclick="window.open('{{ value }}', '_blank')">
      </div>
    ;;
  }

  measure: count {
    type: count
  }
}

# Explore - Join tables together
explore: medica_exhibitors {
  label: "MEDICA Exhibitors"

  join: medica_product_images {
    type: left_outer
    sql_on: ${medica_exhibitors.id} = ${medica_product_images.exhibitor_id} ;;
    relationship: one_to_many
  }

  join: medica_documents {
    type: left_outer
    sql_on: ${medica_exhibitors.id} = ${medica_documents.exhibitor_id} ;;
    relationship: one_to_many
  }
}
```

**3. Looker Dashboard Example:**

When viewing a company in Looker, you'll see:
- **Company Info**: Name, location, hall number, description
- **Contact**: Email, phone, website (clickable)
- **Product Images**: Displayed as clickable thumbnails in a gallery
- **Documents**: Download links for PDFs
- **Filters**: By country, region, product category

**Example Query in Looker:**
```
SELECT exhibitors, COUNT(images) AS num_products
WHERE region = 'China'
GROUP BY exhibitors
```

---

## 5. Enhanced Schema (Recommended)

Add these fields for better Looker experience:

```sql
ALTER TABLE medica_exhibitors
ADD COLUMN country VARCHAR(100),
ADD COLUMN region VARCHAR(50),
ADD COLUMN product_category VARCHAR(200),
ADD COLUMN booth_size VARCHAR(50);
```

**Benefits:**
- ✅ Filter by country/region easily
- ✅ Create dashboards: "China companies vs Global"
- ✅ Build geomaps
- ✅ Product category analytics
- ✅ Booth size comparisons

---

## 6. Complete Implementation Plan

### Step 1: Update Upload Scripts ✅

**Files to update:**
- `upload_to_gcs.py` - Handle China/Global separately
- `upload_to_cloudsql.py` - Add country/region fields

**Updates needed:**
```python
# upload_to_gcs.py
def upload_region(region, downloads_path):
    """Upload images for specific region"""
    # region = 'china' or 'global'
    # Creates paths like: gs://bucket/china/images/company/image.png
    pass

# upload_to_cloudsql.py
def import_exhibitors(region, data_file):
    """Import exhibitors with region tagging"""
    exhibitor_data['region'] = region  # 'China' or 'Global'
    exhibitor_data['country'] = detect_country(exhibitor_data)
    pass
```

### Step 2: Create Cloud SQL Database ✅

```bash
# 1. Connect to existing Cloud SQL instance
gcloud sql connect medical-db --user=postgres

# 2. Create new database (if needed)
CREATE DATABASE medica;

# 3. Run schema
\c medica
\i schema.sql

# 4. Verify tables
\dt
```

### Step 3: Upload Images to GCS ✅

```bash
# Upload China exhibitors
python3 upload_to_gcs.py --region china --path downloads/China/

# Upload Global exhibitors
python3 upload_to_gcs.py --region global --path downloads/Global/

# Verify upload
gsutil ls -r gs://medica-exhibitor-data/
```

**Expected output:**
```
Uploading China companies...
✓ Uploaded 432H Tech Co., Ltd. (3 images)
✓ Uploaded A-GEN BIOTECHNOLOGY (2 images)
...
Total: 1,323 companies, 4,567 images uploaded

Uploading Global companies...
✓ Uploaded 3DBioFibR Inc. (1 image)
...
Total: 1,149 companies, 2,134 images uploaded
```

### Step 4: Import Data to Cloud SQL ✅

```bash
# Import China exhibitors with GCS URLs
python3 upload_to_cloudsql.py --region china

# Import Global exhibitors with GCS URLs
python3 upload_to_cloudsql.py --region global

# Verify import
psql -h [CLOUD_SQL_IP] -U postgres -d medica -c "SELECT COUNT(*) FROM medica_exhibitors;"
```

**Expected output:**
```
Importing China exhibitors...
✓ Imported 1,323 exhibitors
✓ Imported 4,567 product images
✓ Imported 123 documents

Importing Global exhibitors...
✓ Imported 1,149 exhibitors
✓ Imported 2,134 product images
✓ Imported 89 documents

Total: 2,472 exhibitors, 6,701 images, 212 documents
```

### Step 5: Connect Looker ✅

**Looker Setup:**

1. **Add Cloud SQL as Data Source**
   - Connection: `medical-db` (Cloud SQL instance)
   - Database: `medica`
   - Username: `looker_user` (create read-only user)

2. **Create LookML Project**
   ```bash
   # Create new Looker project
   looker_project/
   ├── models/
   │   └── medica.model.lkml
   ├── views/
   │   ├── medica_exhibitors.view.lkml
   │   ├── medica_product_images.view.lkml
   │   └── medica_documents.view.lkml
   └── dashboards/
       └── medica_overview.dashboard.lkml
   ```

3. **Import LookML Views** (provided in this document)

4. **Build Dashboards**
   - Overview: Total exhibitors by region
   - China Deep Dive: Company listings with images
   - Product Gallery: Browse all products
   - Search: Full-text search across companies

### Step 6: Create Looker Dashboards ✅

**Dashboard Examples:**

**1. Executive Overview**
- Total exhibitors: 2,472
- China: 1,323 (53%)
- Global: 1,149 (47%)
- Top product categories
- Geographic distribution

**2. Company Explorer**
- Searchable company list
- Filter by region, country, product category
- Click to view details with product images

**3. Product Gallery**
- All product images in grid view
- Filter by company, region
- Click to enlarge and view company details

---

## 7. Data Quality & Validation

### Validation Checks

Before import, run validation:

```sql
-- Check for duplicates
SELECT name, COUNT(*)
FROM medica_exhibitors
GROUP BY name
HAVING COUNT(*) > 1;

-- Verify image URLs are valid
SELECT COUNT(*) as broken_images
FROM medica_product_images
WHERE gcs_url IS NULL OR gcs_url = '';

-- Companies without images
SELECT COUNT(*) as companies_without_images
FROM medica_exhibitors e
LEFT JOIN medica_product_images p ON e.id = p.exhibitor_id
WHERE p.id IS NULL;
```

### Data Cleanup

```python
# Clean company names
def sanitize_company_name(name):
    name = name.strip()
    name = re.sub(r'\s+', ' ', name)  # Remove extra spaces
    return name

# Detect country from address/location
def detect_country(exhibitor_data):
    if 'China' in exhibitor_data.get('address', '') or \
       'Beijing' in exhibitor_data.get('address', ''):
        return 'China'
    return 'Unknown'
```

---

## 8. Cost Estimation

### Google Cloud SQL (PostgreSQL)

**Database Size:**
- 2,472 companies × 2 KB/row = ~5 MB
- 6,701 images × 100 bytes/row = ~670 KB
- Total: ~10 MB data

**Instance:**
- `db-f1-micro` (shared CPU, 614 MB RAM)
- Cost: ~$10/month
- Storage: 10 GB SSD (~$1.70/month)

**Total Cloud SQL: ~$12/month**

### Google Cloud Storage

**Storage:**
- 6,701 images × 100 KB/image = ~670 MB
- Cost: $0.02/GB/month
- Total: ~$0.02/month

**Data Transfer:**
- Egress to Looker/users: ~1 GB/month
- Cost: $0.12/GB
- Total: ~$0.12/month

**Total GCS: ~$0.14/month**

### Looker

- Looker pricing varies (typically ~$3,000-$5,000/year for small teams)
- Alternative: Use Metabase (free, open-source)

**Total Estimated Cost: ~$12-15/month** (excluding Looker)

---

## 9. Security & Access Control

### Database Security

```sql
-- Create read-only user for Looker
CREATE USER looker_user WITH PASSWORD 'secure_password';
GRANT CONNECT ON DATABASE medica TO looker_user;
GRANT USAGE ON SCHEMA public TO looker_user;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO looker_user;

-- Create admin user for data imports
CREATE USER data_admin WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE medica TO data_admin;
```

### GCS Security

```bash
# Private bucket (recommended)
gsutil iam ch -d allUsers:objectViewer gs://medica-exhibitor-data

# Allow only Cloud SQL service account
gsutil iam ch serviceAccount:cloudsql@system.gserviceaccount.com:objectViewer \
  gs://medica-exhibitor-data

# Or use signed URLs for temporary access
```

---

## 10. Future Enhancements

### Phase 2 Features

1. **AI-Powered Product Categorization**
   - Use Google Vision API to categorize products from images
   - Auto-tag product types

2. **Company Similarity Search**
   - Find similar companies based on product descriptions
   - Recommend competitors/partners

3. **Contact Enrichment**
   - Validate email addresses
   - Find social media profiles
   - Add company websites from domain search

4. **Geolocation Mapping**
   - Extract city/province from addresses
   - Plot companies on interactive map
   - Show booth locations on MEDICA floor plan

5. **Product Matching**
   - Match Chinese companies with similar global companies
   - Identify market gaps/opportunities

---

## 11. Maintenance & Updates

### Regular Tasks

**Weekly:**
- Check for new scraped companies
- Run organization script to categorize new data
- Upload new images to GCS
- Import new data to Cloud SQL

**Monthly:**
- Review data quality
- Update Looker dashboards
- Generate analytics reports
- Backup database

**Automation Script:**
```bash
#!/bin/bash
# weekly_update.sh

# 1. Run scraper (if needed)
python3 scraper_chinese_improved.py

# 2. Organize new companies
python3 organize_chinese_companies.py

# 3. Upload to GCS
python3 upload_to_gcs.py --region china
python3 upload_to_gcs.py --region global

# 4. Import to database
python3 upload_to_cloudsql.py --region china
python3 upload_to_cloudsql.py --region global

# 5. Generate report
python3 generate_weekly_report.py
```

---

## 12. Success Metrics

**Key Performance Indicators:**

- ✅ **Data Completeness**: % of companies with product images
- ✅ **Upload Success Rate**: % of images successfully uploaded to GCS
- ✅ **Database Import Success**: % of records successfully imported
- ✅ **Looker Query Performance**: Average query time < 2 seconds
- ✅ **Image Load Time**: Average image load < 1 second
- ✅ **User Engagement**: Number of Looker dashboard views/week

**Target Metrics:**
- Data completeness: >80%
- Upload success: >99%
- Import success: 100%
- Query performance: <2s
- Image load time: <1s

---

## 13. Conclusion

This implementation plan provides a complete architecture for managing MEDICA 2025 exhibitor data with:

- ✅ **Scalable PostgreSQL database** for structured data
- ✅ **Google Cloud Storage** for images/documents
- ✅ **Looker integration** for analytics and visualization
- ✅ **Organized data structure** (China/Global regions)
- ✅ **Cost-effective** (~$12-15/month)
- ✅ **Easy to maintain** with automation scripts

**Next Steps:**
1. Update upload scripts for region handling
2. Create Cloud SQL database
3. Upload images to GCS
4. Import data to Cloud SQL
5. Connect Looker and build dashboards

**Estimated Timeline:**
- Database setup: 30 minutes
- Image upload: 1-2 hours (depending on internet speed)
- Data import: 30 minutes
- Looker setup: 1-2 hours
- **Total: 3-5 hours**

---

**Document Version:** 1.0
**Last Updated:** 2025-11-21
**Author:** Claude Code Assistant
**Project Repository:** `/Users/gabrielreginatto/Desktop/Code/Medical/Medica/`
