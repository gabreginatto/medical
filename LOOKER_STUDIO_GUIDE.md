# Looker Studio Setup Guide - Complete Beginner's Manual

**For someone with ZERO Looker Studio experience**

---

## Table of Contents
1. [What is Looker Studio?](#what-is-looker-studio)
2. [Prerequisites](#prerequisites)
3. [Step 1: Create SQL Views in Database](#step-1-create-sql-views-in-database)
4. [Step 2: Access Looker Studio](#step-2-access-looker-studio)
5. [Step 3: Connect to Cloud SQL](#step-3-connect-to-cloud-sql)
6. [Step 4: Create Data Sources](#step-4-create-data-sources)
7. [Step 5: Create Your First Dashboard](#step-5-create-your-first-dashboard)
8. [Step 6: Add Charts and Tables](#step-6-add-charts-and-tables)
9. [Common Issues & Troubleshooting](#common-issues--troubleshooting)
10. [Example Dashboards to Create](#example-dashboards-to-create)

---

## What is Looker Studio?

**Looker Studio** (formerly Google Data Studio) is a **free** data visualization tool by Google. Think of it like:
- **Excel pivot tables** - but interactive and live
- **Tableau/Power BI** - but free and web-based
- **Google Sheets charts** - but much more powerful

**What you'll do with it:**
- Connect to your Cloud SQL database
- View the 6 SQL views you created (`vw_curativos`, `vw_high_value_items`, etc.)
- Create interactive dashboards with charts, tables, and filters
- Share reports with your team

**No installation needed** - it's entirely web-based.

---

## Prerequisites

Before starting, make sure you have:

- ✅ Google Account (same one used for Google Cloud)
- ✅ Cloud SQL database running (`pncp_medical_data`)
- ✅ Database password for user `postgres`
- ✅ Cloud SQL instance connection details:
  - Instance name (e.g., `medical-473219:us-central1:pncp-medical-db`)
  - IP address (public IP or private IP if using Cloud SQL Proxy)

**How to find your Cloud SQL connection details:**

```bash
# Run this to get your instance connection name
gcloud sql instances describe pncp-medical-db --format="value(connectionName)"

# Get the public IP address
gcloud sql instances describe pncp-medical-db --format="value(ipAddresses[0].ipAddress)"
```

Write these down - you'll need them later!

---

## Step 1: Create SQL Views in Database

**IMPORTANT:** Before using Looker Studio, you MUST create the views in your database first.

### Option A: Using Cloud SQL Console (Easiest)

1. **Open Google Cloud Console:**
   - Go to: https://console.cloud.google.com
   - Click on "SQL" in the left menu (or search "SQL" in the top search bar)

2. **Select your database:**
   - Click on your instance: `pncp-medical-db`

3. **Open Cloud Shell Editor:**
   - Click the button "OPEN CLOUD SHELL EDITOR" at the top
   - OR click the `>_` icon in top-right corner

4. **Connect to database:**
   ```bash
   gcloud sql connect pncp-medical-db --user=postgres --database=pncp_medical_data
   ```
   - Enter your password when prompted

5. **Run the views SQL file:**

   **First, copy the file content:**
   - On your local machine, run:
   ```bash
   cat /Users/gabrielreginatto/Desktop/Code/Medical/looker_views.sql
   ```
   - Copy the ENTIRE output

   **Then paste into Cloud Shell:**
   - In the Cloud Shell SQL prompt, paste the entire SQL content
   - Press Enter
   - You should see messages like:
     ```
     CREATE VIEW
     CREATE VIEW
     CREATE VIEW
     ...
     ```

6. **Verify views were created:**
   ```sql
   \dv
   ```
   - You should see 6 views listed:
     - `vw_tender_items_complete`
     - `vw_curativos`
     - `vw_mdsap_items`
     - `vw_high_value_items`
     - `vw_items_by_state`
     - `vw_matched_products_analysis`

7. **Exit:**
   ```sql
   \q
   ```

### Option B: Using psql from Your Local Machine

**If you have psql installed locally:**

```bash
# Connect to Cloud SQL
psql -h <YOUR_PUBLIC_IP> -U postgres -d pncp_medical_data

# Run the views file
\i /Users/gabrielreginatto/Desktop/Code/Medical/looker_views.sql

# Verify
\dv

# Exit
\q
```

### Option C: Using Cloud SQL Proxy (Most Secure)

**If you're using Cloud SQL Proxy:**

```bash
# Start proxy in background
./cloud-sql-proxy medical-473219:us-central1:pncp-medical-db &

# Connect via proxy
psql -h 127.0.0.1 -U postgres -d pncp_medical_data

# Run the views file
\i /Users/gabrielreginatto/Desktop/Code/Medical/looker_views.sql

# Verify
\dv

# Exit
\q
```

---

## Step 2: Access Looker Studio

1. **Open Looker Studio:**
   - Go to: https://lookerstudio.google.com
   - Sign in with your Google account (same one used for Google Cloud)

2. **First-time setup:**
   - If this is your first time, you'll see a welcome screen
   - Click "Get Started" or "Create"
   - Accept the terms of service

3. **You should see:**
   - A blank home page with "Create" button
   - Recent reports (empty if first time)
   - Templates gallery

**You're now in Looker Studio!** Next step is connecting to your database.

---

## Step 3: Connect to Cloud SQL

Now we'll connect Looker Studio to your Cloud SQL database.

### 3.1 - Start Creating a Data Source

1. **Click "Create"** (top-left corner)
2. **Select "Data source"**
3. **You'll see a list of connectors** - scroll down and find:
   - **"Cloud SQL for PostgreSQL"**
   - Click on it

### 3.2 - Enter Connection Details

You'll see a form with several fields. Fill them out carefully:

**Field 1: Instance connection name**
- Format: `project-id:region:instance-name`
- Example: `medical-473219:us-central1:pncp-medical-db`
- **How to get this:** Run `gcloud sql instances describe pncp-medical-db --format="value(connectionName)"`

**Field 2: Database**
- Enter: `pncp_medical_data`

**Field 3: Username**
- Enter: `postgres`

**Field 4: Password**
- Enter your database password
- Click the checkbox "Enable SSL" if available (recommended)

**Field 5: Table or Custom Query**
- **IMPORTANT:** Select "Custom Query" (NOT "Table")
- This is where we'll select our views

### 3.3 - Test Connection

1. **Click "AUTHENTICATE"** button
2. **If successful:**
   - You'll see a green checkmark
   - The "Custom Query" box will become active

3. **If failed:**
   - Check your connection details
   - Make sure Cloud SQL allows connections from Looker Studio
   - See [Troubleshooting](#common-issues--troubleshooting) section below

### 3.4 - Enable Looker Studio Access (If Connection Fails)

**If you get "Connection refused" or "Access denied":**

You need to whitelist Looker Studio IP addresses in Cloud SQL:

1. **Go to Cloud SQL Console:**
   - https://console.cloud.google.com/sql

2. **Click on your instance:** `pncp-medical-db`

3. **Click "Connections" tab** (left side)

4. **Under "Authorized networks":**
   - Click "ADD NETWORK"
   - Name: `Looker Studio`
   - Network: `0.0.0.0/0` (allows all IPs - for testing)
   - **Note:** For production, use specific Looker Studio IP ranges (see Google docs)

5. **Click "DONE"** then **"SAVE"**

6. **Wait 1-2 minutes** for changes to apply

7. **Try connecting again** in Looker Studio

---

## Step 4: Create Data Sources

Now we'll create 6 separate data sources - one for each view.

### 4.1 - Create First Data Source: `vw_tender_items_complete`

1. **In the "Custom Query" box, enter:**
   ```sql
   SELECT * FROM vw_tender_items_complete
   ```

2. **Click "CONNECT"** (top-right)

3. **You'll see a schema preview:**
   - All columns from the view will be listed
   - Data types shown (Text, Number, Date, etc.)
   - Sample data preview

4. **Verify the columns:**
   - You should see: `item_id`, `item_description`, `quantity`, `state_code`, `organization_name`, etc.

5. **Name your data source:**
   - Top-left corner, click "Untitled Data Source"
   - Rename to: **"PNCP - All Tender Items"**

6. **Click "CREATE REPORT"** (top-right)
   - For now, click "CANCEL" when it asks to create a report
   - We'll create reports later

7. **Data source is saved!**

### 4.2 - Create Second Data Source: `vw_curativos`

1. **Go back to Looker Studio home:**
   - Click the Looker Studio logo (top-left)

2. **Click "Create" → "Data source"**

3. **Select "Cloud SQL for PostgreSQL"** again

4. **Enter same connection details as before:**
   - Instance connection name: `medical-473219:us-central1:pncp-medical-db`
   - Database: `pncp_medical_data`
   - Username: `postgres`
   - Password: [your password]

5. **Click "AUTHENTICATE"**

6. **In "Custom Query" box, enter:**
   ```sql
   SELECT * FROM vw_curativos
   ```

7. **Click "CONNECT"**

8. **Rename data source to:** **"PNCP - Curativos"**

9. **Click "CREATE REPORT"** → Cancel for now

### 4.3 - Create Remaining Data Sources

Repeat the process above for each view:

**Data Source 3:**
- Name: **"PNCP - MDSAP Items"**
- Query: `SELECT * FROM vw_mdsap_items`

**Data Source 4:**
- Name: **"PNCP - High Value Tenders"**
- Query: `SELECT * FROM vw_high_value_items`

**Data Source 5:**
- Name: **"PNCP - Items by State"**
- Query: `SELECT * FROM vw_items_by_state`

**Data Source 6:**
- Name: **"PNCP - Matched Products"**
- Query: `SELECT * FROM vw_matched_products_analysis`

**When done, you should have 6 data sources saved!**

---

## Step 5: Create Your First Dashboard

Let's create a simple dashboard to visualize curativos (wound care products).

### 5.1 - Start New Report

1. **Click "Create" → "Report"**

2. **Add a data source:**
   - Find and select: **"PNCP - Curativos"**
   - Click "ADD TO REPORT"

3. **You'll see a blank canvas with a table**
   - This is your report editor

### 5.2 - Add a Title

1. **Click "Text" in the toolbar** (top)
2. **Click on the canvas** to place text box
3. **Type:** "Curativos Analysis Dashboard"
4. **Format:**
   - Select the text
   - Use toolbar to make it larger, bold, centered
   - Change color if desired

### 5.3 - Add a Summary Card (Total Items)

1. **Click "Add a chart"** (toolbar)
2. **Select "Scorecard"**
3. **Click on canvas** to place it
4. **Configure the scorecard:**
   - **Metric:** Find "Record Count" (or "item_id" and change aggregation to "Count")
   - **Label:** "Total Curativo Items"

You should see a number showing total curativo items in database!

### 5.4 - Add a Bar Chart (Items by State)

1. **Click "Add a chart" → "Bar chart"**
2. **Place it on canvas**
3. **Configure:**
   - **Dimension:** `state_code`
   - **Metric:** `Record Count`
   - **Sort:** By metric, descending

You'll see a bar chart showing which states have most curativo items!

### 5.5 - Add a Table (Top Items)

1. **Click "Add a chart" → "Table"**
2. **Place below the chart**
3. **Configure:**
   - **Dimensions:**
     - `item_description`
     - `quantity`
     - `homologated_unit_value`
     - `state_code`
     - `organization_name`
   - **Metric:** None needed
   - **Rows per page:** 10

4. **Add sorting:**
   - Click on `homologated_unit_value` column header
   - Select "Sort descending"

Now you have a table showing top curativo items by value!

### 5.6 - Save Your Report

1. **Click "File" → "Save"** (top-left)
2. **Name:** "Curativos Dashboard"
3. **Click "SAVE"**

**Congratulations! You just created your first Looker Studio dashboard!**

---

## Step 6: Add Charts and Tables

Here are common chart types you can add:

### Chart Type 1: Scorecard (Summary Numbers)

**What it shows:** Single number (total, average, sum, etc.)

**Best for:**
- Total items
- Total value
- Average price
- Count of organizations

**How to add:**
1. Add chart → Scorecard
2. Metric: Choose field and aggregation (Count, Sum, Average)
3. Optional: Add comparison period

**Example:**
- Metric: `homologated_total_value` (Sum)
- Label: "Total Market Value (R$)"

### Chart Type 2: Bar Chart

**What it shows:** Comparison across categories

**Best for:**
- Items by state
- Items by organization type
- Top organizations by spend

**How to add:**
1. Add chart → Bar chart
2. Dimension: Category field (e.g., `state_code`)
3. Metric: Number to compare (e.g., `Record Count`)
4. Sort: Descending by metric

### Chart Type 3: Time Series (Line Chart)

**What it shows:** Trends over time

**Best for:**
- Tenders published over time
- Monthly value trends
- Seasonal patterns

**How to add:**
1. Add chart → Time series
2. Dimension: `publication_date`
3. Metric: `Record Count` or `homologated_total_value` (Sum)

### Chart Type 4: Pie Chart

**What it shows:** Parts of a whole (percentages)

**Best for:**
- Distribution by government level (Federal, Estadual, Municipal)
- Item value categories
- Tender value categories

**How to add:**
1. Add chart → Pie chart
2. Dimension: Category field (e.g., `government_level`)
3. Metric: What to measure (e.g., `Record Count`)

### Chart Type 5: Geo Map

**What it shows:** Geographic distribution

**Best for:**
- Tender density by state
- Total value by state
- Organization count by state

**How to add:**
1. Add chart → Geo map → Brazil
2. Dimension: `state_code`
3. Metric: `Record Count` or `total_value_brl` (Sum)
4. Map will color states by intensity

### Chart Type 6: Table

**What it shows:** Detailed row-level data

**Best for:**
- Item listings
- Tender details
- Winner information

**How to add:**
1. Add chart → Table
2. Dimensions: Fields to show as columns
3. Metrics: Aggregated fields (optional)
4. Rows per page: 10-50

### Adding Filters

**Want to filter your dashboard?**

1. **Click "Add a control" → "Drop-down list"**
2. **Configure:**
   - Control field: `state_code` (or any field)
   - Label: "Select State"
3. **Place at top of dashboard**

Now users can filter entire dashboard by state!

**Other useful filters:**
- Date range picker (for `publication_date`)
- Drop-down for `government_level`
- Drop-down for `item_value_category`

---

## Common Issues & Troubleshooting

### Issue 1: "Connection refused" or "Can't connect to database"

**Solutions:**

1. **Check Cloud SQL authorized networks:**
   ```bash
   # Check current authorized networks
   gcloud sql instances describe pncp-medical-db --format="value(settings.ipConfiguration.authorizedNetworks)"

   # Add Looker Studio access (allows all IPs - for testing)
   gcloud sql instances patch pncp-medical-db --authorized-networks=0.0.0.0/0
   ```

2. **Verify database is running:**
   ```bash
   gcloud sql instances list
   ```
   - Status should be "RUNNABLE"

3. **Check credentials:**
   - Username: `postgres`
   - Database: `pncp_medical_data`
   - Password: correct password

### Issue 2: "Table or view not found"

**Solution:**

Views not created yet! Go back to [Step 1](#step-1-create-sql-views-in-database)

**Verify views exist:**
```bash
# Connect to database
gcloud sql connect pncp-medical-db --user=postgres --database=pncp_medical_data

# List views
\dv

# Should see 6 views listed
```

### Issue 3: "No data available" in charts

**Possible causes:**

1. **Views are empty** - Check if main.py has been run to populate data:
   ```bash
   # Count items in base table
   SELECT COUNT(*) FROM tender_items;
   ```
   - If 0, run: `python3 main.py --start 20250101 --end 20250131 --states SP`

2. **Query is too restrictive** - Some views filter data:
   - `vw_curativos` only shows items with "curativo", "bandagem", "malha tubular"
   - `vw_high_value_items` only shows tenders >R$20M with ≤10 items
   - If no data matches, chart will be empty

3. **Wrong data source selected** - Make sure chart uses correct data source

### Issue 4: Charts showing wrong numbers

**Solutions:**

1. **Check aggregation:**
   - Click on chart
   - In right panel, check "Metric" field
   - Change aggregation: Sum, Count, Average, etc.

2. **Check field type:**
   - Text fields can't be summed
   - Date fields need special handling
   - Numbers should be "Number" type (not "Text")

3. **Fix field type:**
   - Go to data source (not report)
   - Click on field
   - Change type: Number, Currency, Percent, etc.

### Issue 5: "Cloud SQL connector not found"

**Solution:**

Make sure you're using:
- **"Cloud SQL for PostgreSQL"** connector
- NOT "PostgreSQL" (generic connector)
- NOT "Cloud SQL for MySQL"

Scroll through connector list carefully!

### Issue 6: Report is slow to load

**Solutions:**

1. **Add date filters:**
   - Limit to recent months instead of all data

2. **Use aggregated views:**
   - Use `vw_items_by_state` (pre-aggregated) instead of `vw_tender_items_complete`

3. **Limit table rows:**
   - Set "Rows per page" to 10-20 instead of 100+

4. **Consider materialized views** (advanced):
   - For very large datasets, materialize views in database
   - Refresh daily via cron job

---

## Example Dashboards to Create

Here are some useful dashboards you can build:

### Dashboard 1: Executive Summary

**Data Source:** `vw_items_by_state`

**Charts:**
1. **Scorecard:** Total tenders
2. **Scorecard:** Total market value (R$)
3. **Scorecard:** Average item value
4. **Geo Map:** Tenders by state (colored by count)
5. **Bar Chart:** Top 10 states by value
6. **Table:** State summary (tenders, items, total value)

**Filters:**
- Date range picker

### Dashboard 2: Curativos Analysis

**Data Source:** `vw_curativos`

**Charts:**
1. **Scorecard:** Total curativo items
2. **Scorecard:** Total market value
3. **Pie Chart:** Distribution by government level
4. **Bar Chart:** Items by state
5. **Time Series:** Curativos published over time
6. **Table:** Top curativo items (sorted by value)

**Filters:**
- State drop-down
- Date range picker

### Dashboard 3: High-Value Opportunities

**Data Source:** `vw_high_value_items`

**Charts:**
1. **Scorecard:** Count of high-value tenders
2. **Scorecard:** Total opportunity value
3. **Pie Chart:** Distribution by tender value category (Mega, Very High, High)
4. **Table:** Tender details (control_number, organization, state, total_value, item_count)
5. **Bar Chart:** High-value tenders by state

**Filters:**
- Tender value category drop-down
- State drop-down

### Dashboard 4: Product Matching Results

**Data Source:** `vw_matched_products_analysis`

**Charts:**
1. **Scorecard:** Total matches
2. **Scorecard:** Total potential savings (R$)
3. **Scorecard:** Average match confidence
4. **Pie Chart:** Distribution by opportunity level (High, Medium, Low)
5. **Bar Chart:** Savings by state
6. **Table:** Match details (fernandes_product, tender_item, market_price, fernandes_price, savings, confidence)

**Filters:**
- Opportunity level drop-down
- Match confidence slider (70-100%)
- State drop-down

### Dashboard 5: Geographic Analysis

**Data Source:** `vw_items_by_state`

**Charts:**
1. **Geo Map:** Brazil map colored by total value
2. **Bar Chart:** Top states by tender count
3. **Bar Chart:** Top states by organization count
4. **Scatter Chart:** Tender count vs. Total value (by state)
5. **Table:** Full state breakdown

**Filters:**
- None needed (shows all states)

---

## Next Steps

**After completing this guide:**

1. **Create all 6 data sources** (from Step 4)
2. **Build 2-3 dashboards** (from examples above)
3. **Share with your team:**
   - Click "Share" button (top-right of report)
   - Add email addresses
   - Set permissions: "Can view" or "Can edit"

4. **Set up daily data refresh:**
   - Data sources auto-refresh when report is opened
   - For scheduled refresh, use Cloud Scheduler to run main.py daily

5. **Explore more:**
   - Try different chart types
   - Combine data sources (blended data)
   - Add calculated fields
   - Create interactive drill-downs

---

## Useful Resources

**Looker Studio Documentation:**
- Official Guide: https://support.google.com/looker-studio
- Video Tutorials: https://www.youtube.com/c/GoogleDataStudio
- Community Gallery: https://lookerstudio.google.com/gallery

**For Questions:**
- Google Cloud SQL: https://cloud.google.com/sql/docs
- Looker Studio Community: https://support.google.com/looker-studio/community

---

## Quick Reference Card

**Most Common Actions:**

| Task | How to Do It |
|------|--------------|
| **Create new report** | Create → Report |
| **Add data source to report** | Resource → Manage added data sources → Add |
| **Add chart** | Toolbar → Add a chart → [type] |
| **Add filter** | Toolbar → Add a control → Drop-down/Date range |
| **Change chart type** | Click chart → Setup tab → Chart type |
| **Rename field** | Click field → Rename |
| **Format numbers** | Data source → Field → Type → Currency/Percent |
| **Sort table** | Click column header → Sort ascending/descending |
| **Download data** | Chart → More options (⋮) → Export → CSV |
| **Share report** | Top-right → Share → Add email |
| **Make copy** | File → Make a copy |

---

**That's it! You're now ready to use Looker Studio with your PNCP medical data.**

**Start with the Curativos Dashboard (easiest) and build from there.** 🚀
