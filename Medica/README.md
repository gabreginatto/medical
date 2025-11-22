# MEDICA 2025 Exhibitor Scraper & Database Uploader

Scrapes Chinese exhibitor data from MEDICA 2025 trade fair and uploads to Google Cloud Platform.

## Overview

This project scrapes exhibitor information, product images, and documents from the MEDICA trade fair website and stores them in:
- **Cloud SQL (PostgreSQL)** - Structured exhibitor data
- **Cloud Storage** - Product images and documents

## Files

### Scraping
- `scraper_combined.py` - Main scraper (all exhibitors, headless)
- `test_combined.py` - Test scraper (first 3 exhibitors, visible browser)
- `requirements.txt` - Python dependencies

### Database & Upload
- `schema.sql` - PostgreSQL database schema
- `upload_to_gcs.py` - Upload images/docs to Cloud Storage
- `upload_to_cloudsql.py` - Import data to Cloud SQL

### Output Files (generated after scraping)
- `downloads/` - Individual exhibitor folders with images and JSON
- `exhibitors_summary.json` - Complete scraped data
- `exhibitors_for_database.csv` - CSV for database import
- `exhibitors_with_gcs_urls.json` - Data with Cloud Storage URLs

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the Scraper

```bash
# Full scrape (all exhibitors)
python3 scraper_combined.py

# Test run (first 3 exhibitors only)
python3 test_combined.py
```

This will create:
- `downloads/` folder with all exhibitor data
- `exhibitors_summary.json` with complete data
- `exhibitors_for_database.csv` for database import

### 3. Set Up Google Cloud Platform

#### Create Cloud Storage Bucket

```bash
# Set your project
gcloud config set project medical-473219

# Create bucket for exhibitor data
gsutil mb -l us-central1 gs://medica-exhibitor-data

# Optional: Make bucket publicly readable
# gsutil iam ch allUsers:objectViewer gs://medica-exhibitor-data
```

#### Set Up Cloud SQL Database

```bash
# If you don't have a Cloud SQL instance, create one:
gcloud sql instances create medical-db \
    --database-version=POSTGRES_14 \
    --tier=db-f1-micro \
    --region=us-central1

# Create database
gcloud sql databases create medical --instance=medical-db

# Run schema
psql -h YOUR_CLOUD_SQL_IP -U YOUR_USER -d medical -f schema.sql
```

### 4. Upload to Cloud Storage

```bash
# Make sure you're authenticated
gcloud auth application-default login

# Upload all images and documents
python3 upload_to_gcs.py
```

This creates `exhibitors_with_gcs_urls.json` with Cloud Storage URLs.

### 5. Import to Cloud SQL

```bash
# Update upload_to_cloudsql.py with your database credentials
# Then run:
python3 upload_to_cloudsql.py
```

## Database Schema

### Tables

**medica_exhibitors**
- Core exhibitor information (name, location, contact details)

**medica_product_images**
- Product images with Cloud Storage URLs
- Links to exhibitor via `exhibitor_id`

**medica_documents**
- PDF documents with Cloud Storage URLs
- Links to exhibitor via `exhibitor_id`

### Sample Query

```sql
SELECT
    e.name,
    e.location,
    e.email,
    e.website,
    COUNT(DISTINCT p.id) as num_images,
    COUNT(DISTINCT d.id) as num_docs
FROM medica_exhibitors e
LEFT JOIN medica_product_images p ON e.id = p.exhibitor_id
LEFT JOIN medica_documents d ON e.id = d.exhibitor_id
GROUP BY e.id, e.name, e.location, e.email, e.website
ORDER BY e.name;
```

## Data Structure

Each exhibitor record includes:
```json
{
  "name": "Company Name",
  "location": "Hall 16 / B77-1",
  "company_description": "Company info...",
  "email": "info@company.com",
  "phone": "+86 123 4567890",
  "website": "https://www.company.com",
  "address": "Street, City, Country",
  "raw_text": "Full page text content",
  "product_images": ["product_1.png", "product_2.png"],
  "documents": ["brochure.pdf"],
  "event": "MEDICA 2025",
  "scraped_at": "2025-11-20T17:48:00"
}
```

## Configuration

Edit these variables in the scripts as needed:

**upload_to_gcs.py:**
- `PROJECT_ID` - Your GCP project ID
- `BUCKET_NAME` - Cloud Storage bucket name
- `BASE_PATH` - Folder structure in bucket

**upload_to_cloudsql.py:**
- Database connection settings (or use existing `config.py`)

## Troubleshooting

**Playwright not installed:**
```bash
playwright install chromium
```

**GCP authentication:**
```bash
gcloud auth application-default login
```

**Database connection:**
- Ensure Cloud SQL instance allows your IP
- Check credentials in upload_to_cloudsql.py

## Project Info

- **Event:** MEDICA 2025
- **Source:** https://www.medica-tradefair.com
- **Filter:** Chinese exhibitors only
- **Data:** Company info, product images, contact details
