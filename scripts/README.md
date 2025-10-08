# Scripts Directory

Organized utility scripts for PNCP Medical processing workflow.

## 📁 Directory Structure

### `/batch` - Batch Processing Scripts
Bulk tender and item extraction workflows.

- **`run_monthly_batches.py`** - Run tender discovery for specific month ranges
- **`fetch_and_save_items_improved.py`** - Fetch missing items for tenders that lack them

### `/analytics` - Analytics & Reporting
Database views and analytics setup for reporting/dashboards.

- **`analytics_views.sql`** - SQL views for analytics (super_tenders, etc.)
- **`create_super_tenders_view.py`** - Create super_tenders materialized view
- **`refresh_views.py`** - Refresh all materialized views
- **`run_analytics_setup.py`** - Complete analytics setup workflow
- **`update_super_tenders.py`** - Update super_tenders view data
- **`export_super_tenders.py`** - Export super_tenders to CSV

### `/debug` - Debug & Inspection Tools
Ad-hoc scripts for database inspection and debugging.

- **`check_db_stats.py`** - Show database statistics
- **`check_matched_products.py`** - Inspect matched products
- **`check_rs_stats.py`** - Rio Grande do Sul tender statistics
- **`check_schema.py`** - Inspect database schema
- **`check_tender_dates.py`** - Check tender date ranges
- **`show_tenders_4_to_8.py`** - Show tenders 4-8 for inspection
- **`show_top_3_tenders.py`** - Show top 3 tenders by value
- **`show_top_tender_items.py`** - Show top tender items

## 🚀 Usage

All scripts should be run from the project root:

```bash
# Batch processing
python3 scripts/batch/run_monthly_batches.py

# Analytics setup
python3 scripts/analytics/run_analytics_setup.py

# Debugging
python3 scripts/debug/check_db_stats.py
```

## ⚠️ Note

These are utility scripts separate from the main workflow (`main.py`). Use them for:
- One-off batch operations
- Database inspection
- Analytics/reporting setup
- Debugging specific issues

For the standard daily workflow, use `main.py` instead.
