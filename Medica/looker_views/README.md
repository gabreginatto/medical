# MEDICA 2025 Exhibitor Data - Looker Setup Guide

This directory contains LookML files for visualizing MEDICA 2025 exhibitor data in Looker, including product images and documents from Google Cloud Storage.

## 📁 Files Overview

### Views
- **`medica_exhibitors.view.lkml`** - Main exhibitor information (name, location, contact, etc.)
- **`medica_product_images.view.lkml`** - Product images with inline display capabilities
- **`medica_documents.view.lkml`** - PDF documents and catalogs

### Model
- **`medica.model.lkml`** - Data model with explores for all exhibitors, China-only, and Global-only

### Dashboards
- **`medica_china_overview.dashboard.lookml`** - Overview dashboard with key metrics
- **`medica_product_catalog.dashboard.lookml`** - Product catalog browser with image gallery

## 🚀 Setup Instructions

### 1. Create Looker Connection

In your Looker instance, create a new database connection:

**Connection Name:** `medical_cloud_sql`

**Database Type:** PostgreSQL

**Connection Settings:**
```
Host: 34.134.110.78 (or your Cloud SQL instance IP)
Port: 5432
Database: medica
Username: gabrielreginatto@gmail.com (Cloud IAM user)
```

**Authentication:** Use Cloud IAM authentication (recommended) or service account

**SSL:** Required (Cloud SQL default)

### 2. Upload LookML Files to Looker

#### Option A: Via Looker IDE
1. Go to **Develop** > **Manage LookML Projects**
2. Create a new project called `medica_exhibitors`
3. Upload all `.lkml` files from this directory
4. Commit changes to production

#### Option B: Via Git Integration
1. Connect your Looker project to a Git repository
2. Push these LookML files to your repository
3. Pull changes in Looker IDE
4. Deploy to production

### 3. Configure GCS Image Access

For product images to display in Looker, ensure:

**GCS Bucket:** `medica-exhibitor-data`

**Access:** Make bucket or specific paths publicly readable, OR use signed URLs

**Public Access (Simpler):**
```bash
gsutil iam ch allUsers:objectViewer gs://medica-exhibitor-data/china/images
```

**Signed URLs (More Secure):**
Modify the `product_image` dimension in `medica_product_images.view.lkml` to generate signed URLs

### 4. Test the Setup

1. Go to **Explore** > **China Exhibitors**
2. Select dimensions:
   - Medica Exhibitors → Name
   - Medica Exhibitors → Location
   - Medica Product Images → Product Image
3. Add filter: **Medica Product Images Count > 0**
4. Run query - you should see exhibitor names with product images

## 📊 Using the Dashboards

### China Exhibitors Overview Dashboard
**Purpose:** High-level metrics and distribution analysis

**Key Metrics:**
- Total exhibitors
- Exhibitors with product images
- Total images and documents
- Distribution by location (hall)
- Images per exhibitor distribution

**Usage:**
1. Navigate to **Dashboards** > **MEDICA China Overview**
2. Use filters to search by name or location
3. Click on any metric to drill into details

### Product Catalog Dashboard
**Purpose:** Browse exhibitor product catalogs

**Features:**
- **Product Image Gallery** - Visual grid of all exhibitor products
- **Top Exhibitors** - Companies with most product images
- **Storage Statistics** - Data usage metrics

**Usage:**
1. Navigate to **Dashboards** > **MEDICA Product Catalog**
2. Search for specific exhibitors
3. Adjust "Minimum Number of Images" slider to filter
4. Click on images to open full size in new tab

## 🎨 Key Features

### Image Display Dimensions

The `medica_product_images` view includes multiple image display options:

- **`product_image`** - Standard size (200x200px)
- **`product_image_thumbnail`** - Small size (100x100px)
- **`product_image_link`** - Clickable, opens full size
- **`image_gallery`** - Formatted for catalog view
- **`first_image`** (measure) - Shows only first product image

**Example Usage:**
```lookml
# In an explore, select:
- medica_exhibitors.name
- medica_product_images.image_gallery
- medica_product_images.count
```

### Filtering Options

**By Region:**
- Use `china_exhibitors` explore for China-only data
- Use `global_exhibitors` explore for non-China data
- Use `medica_exhibitors` explore for all data

**By Content:**
- Filter by `medica_product_images.count > 0` for exhibitors with images
- Filter by `medica_documents.count > 0` for exhibitors with PDFs
- Filter by `medica_exhibitors.email: -NULL` for exhibitors with contact info

## 📈 Sample Queries

### Exhibitors with Most Product Images
```sql
SELECT
  name,
  location,
  COUNT(DISTINCT medica_product_images.id) as image_count
FROM medica_exhibitors
LEFT JOIN medica_product_images ON medica_exhibitors.id = medica_product_images.exhibitor_id
WHERE region = 'China'
GROUP BY name, location
ORDER BY image_count DESC
LIMIT 50;
```

### Storage Usage by Region
```sql
SELECT
  region,
  COUNT(DISTINCT medica_exhibitors.id) as exhibitors,
  COUNT(DISTINCT medica_product_images.id) as images,
  SUM(medica_product_images.file_size_bytes) / 1024.0 / 1024.0 as total_mb
FROM medica_exhibitors
LEFT JOIN medica_product_images ON medica_exhibitors.id = medica_product_images.exhibitor_id
GROUP BY region;
```

## 🔧 Customization

### Adding Custom Dimensions

To add custom fields to the views:

1. Edit the `.view.lkml` file
2. Add new dimension block:
```lookml
dimension: custom_field {
  type: string
  sql: ${TABLE}.custom_column ;;
}
```
3. Commit changes
4. Refresh explores

### Modifying Image Display Size

Edit `medica_product_images.view.lkml`:

```lookml
dimension: product_image {
  type: string
  sql: ${gcs_url} ;;
  html: <img src="{{ value }}" style="max-width: 300px; max-height: 300px;"> ;;
}
```

### Adding New Dashboards

1. Create new `.dashboard.lookml` file
2. Define dashboard structure
3. Add elements (visualizations)
4. Configure filters
5. Commit to production

## 📖 Documentation

### Looker Dimension Types
- `string` - Text fields
- `number` - Numeric fields
- `time` - Date/datetime fields (with timeframes)
- `yesno` - Boolean fields

### HTML Rendering

Looker supports HTML in dimension definitions for:
- Images (`<img>` tags)
- Links (`<a>` tags)
- Custom formatting (`<div>`, `<span>` with inline styles)

**Security Note:** HTML rendering requires `html:` parameter in LookML

## 🆘 Troubleshooting

### Images Not Displaying

**Problem:** Product images show broken links

**Solutions:**
1. Check GCS bucket permissions
2. Verify `gcs_url` format in database
3. Test GCS URL directly in browser
4. Enable CORS on GCS bucket if needed

### Connection Errors

**Problem:** Looker can't connect to Cloud SQL

**Solutions:**
1. Check Cloud SQL instance is running
2. Verify IP address in connection settings
3. Ensure authorized networks include Looker IP
4. Test connection in Looker connection settings

### Slow Dashboard Performance

**Solutions:**
1. Add aggregate tables for common queries
2. Use persistent derived tables (PDTs)
3. Adjust `datagroup` cache settings in model
4. Limit initial dashboard query rows

## 📞 Support

For questions or issues:
- Check Looker documentation: https://docs.looker.com/
- Review Cloud SQL connection guide
- Test queries in SQL Runner first

## 🎯 Next Steps

1. **Connect to Looker** - Set up database connection
2. **Upload LookML** - Add files to your project
3. **Test Explores** - Verify data loads correctly
4. **View Dashboards** - Access pre-built visualizations
5. **Customize** - Modify views and dashboards for your needs

## 📊 Data Summary

- **Database:** `medica` in Cloud SQL PostgreSQL
- **Tables:** 3 (exhibitors, product_images, documents)
- **China Exhibitors:** 1,321
- **Storage Location:** `gs://medica-exhibitor-data/china/`
- **Image Format:** JPG/PNG
- **Document Format:** PDF
