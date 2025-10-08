# Looker Studio Analytics Views Guide

## 📊 Available Views

You now have **5 materialized views** ready for Looker Studio visualization:

### 1. **analytics.curativo_items** (3,761 rows)
**All wound dressing items with complete details**

**Best for:**
- Price analysis for curativos, bandages, gauze
- Organization spending patterns
- State-by-state comparison
- Price variance analysis (estimated vs homologated)

**Key Fields:**
- `description` - Item description
- `homologated_unit_value` - Final price
- `quantity` - Amount purchased
- `organization_name` - Buyer organization
- `state_code` - State
- `tender_year` - Year
- `price_variance_percent` - Price difference %
- `catmat_codes` - Medical classification codes

**Example Dashboards:**
- Top 10 most expensive curativos by state
- Average curativo prices over time
- Organizations spending most on wound care
- Price variance distribution

---

### 2. **analytics.medical_items_summary** (0 rows currently)
**High-confidence medical items with CATMAT codes**

**Best for:**
- CATMAT code analysis
- Medical equipment categorization
- Confidence scoring

**Key Fields:**
- `category` - Auto-categorized (Curativos, Cirúrgico, Luvas, etc.)
- `medical_confidence_score` - AI confidence (70-100%)
- `catmat_codes` - Classification codes
- `description` - Item description

**Note:** Currently empty - will populate as CATMAT data is collected

---

### 3. **analytics.state_summary** (3 rows)
**State-level aggregated statistics**

**Best for:**
- Executive dashboards
- Geographic heatmaps
- State comparison

**Key Fields:**
- `state_code` - State
- `total_tenders` - Number of tenders
- `total_organizations` - Number of buyers
- `total_items` - Number of items
- `medical_items_count` - Medical items count
- `curativo_items_count` - Curativo items count
- `total_homologated_value_brl` - Total spending
- `avg_unit_price_brl` - Average price

**Example Dashboards:**
- Brazil map with spending by state
- State rankings by total value
- Medical items distribution across states

---

### 4. **analytics.top_winners** (4,018 rows)
**Top supplier companies winning contracts**

**Best for:**
- Competitive intelligence
- Supplier analysis
- Market share analysis

**Key Fields:**
- `winner_cnpj` - Supplier tax ID
- `winner_name` - Company name
- `tenders_won` - Number of tenders won
- `items_won` - Number of items won
- `total_value_won_brl` - Total contract value
- `avg_unit_price` - Average price
- `curativo_items` - Curativo items won
- `states_active` - Number of states
- `states_list` - List of states

**Example Dashboards:**
- Top 20 suppliers by revenue
- Supplier geographic presence
- Market concentration analysis
- New entrants vs established players

---

### 5. **analytics.super_tenders** ⭐ (5,166 rows)
**High-value tenders with very few items (2-5 items)**

**Best for:**
- Specialized equipment opportunities
- High-value contract analysis
- Strategic targeting

**Key Fields:**
- `total_homologated_value` - Total value (R$50K minimum)
- `item_count` - Number of items (2-5)
- `avg_value_per_item` - Average per item
- `efficiency_score` - Value/items ratio
- `value_category` - Size category (Small/Medium/Large/Mega)
- `organization_name` - Buyer
- `state_code` - State
- `control_number` - Tender ID

**Example Dashboards:**
- Top 50 super tenders by value
- Efficiency score distribution
- Organizations buying specialized equipment
- Mega tenders (>R$1M) analysis

**Top 5 Super Tenders:**
1. R$532M with 5 items (avg R$106M/item) - SP
2. R$469M with 3 items (avg R$156M/item) - SP
3. R$330M with 2 items (avg R$165M/item) - SP
4. R$245M with 5 items (avg R$49M/item) - PR
5. R$201M with 4 items (avg R$50M/item) - SP

---

## 🚀 Connecting to Looker Studio

### Step 1: Create Data Source
1. Go to [Looker Studio](https://lookerstudio.google.com/)
2. Click **Create** → **Data Source**
3. Search for **"PostgreSQL"** and select **Cloud SQL for PostgreSQL**

### Step 2: Enter Connection Details
```
Project ID: medical-473219
Region: us-central1
Instance ID: pncp-medical-db
Database: pncp_medical_data
```

### Step 3: Authenticate
- **Option A**: Use IAM authentication (gabrielreginatto@gmail.com)
- **Option B**: Use postgres user with password: TempPass123!

### Step 4: Select Schema
- Schema: `analytics`
- Select one of the 5 tables above

### Step 5: Create Report
Click **Create Report** and start building visualizations!

---

## 📈 Recommended Dashboard Ideas

### Dashboard 1: Executive Overview
**Data Source:** `analytics.state_summary`
- **Geo Chart**: Total spending by state
- **Scorecard**: Total tenders, total items, total value
- **Bar Chart**: Top 10 states by medical items
- **Time Series**: Tender growth over time

---

### Dashboard 2: Curativo Market Analysis
**Data Source:** `analytics.curativo_items`
- **Table**: Top 20 most expensive curativo items
- **Pie Chart**: Spending by state
- **Line Chart**: Average curativo price over time
- **Bar Chart**: Top 10 organizations by curativo spending
- **Scatter Plot**: Quantity vs Price (find outliers)

---

### Dashboard 3: Supplier Intelligence
**Data Source:** `analytics.top_winners`
- **Table**: Top 50 suppliers by revenue
- **Bar Chart**: Market share (top 10 suppliers)
- **Geo Chart**: Supplier presence by state
- **Bubble Chart**: Revenue vs # of states (size = # items)
- **Filter**: State, item type, date range

---

### Dashboard 4: Super Tenders Tracker ⭐
**Data Source:** `analytics.super_tenders`
- **Table**: Top 100 super tenders (sortable by value, efficiency)
- **Bar Chart**: Value category distribution
- **Scatter Plot**: Item count vs Total value
- **Heat Map**: Super tenders by state
- **Filters**: State, value range, item count

**Recommended Filters:**
- Value Category: Small/Medium/Large/Mega
- Item Count: 2, 3, 4, 5
- State: All states
- Year: 2024, 2025

---

## 🔄 Refreshing Data

When you add more data to your database, refresh the views:

```bash
python3 refresh_views.py
```

This will update all 5 views with the latest data. Looker Studio will automatically pick up the changes.

---

## 💡 Pro Tips

### 1. **Use Filters Everywhere**
Add state, date, and value filters to all dashboards for interactive exploration.

### 2. **Create Calculated Fields**
- **Price per kg/unit**: For standardized comparison
- **Market share %**: Revenue / Total revenue
- **Year-over-year growth**: Compare 2024 vs 2025

### 3. **Set Up Alerts**
Configure email alerts for:
- New super tenders >R$100M
- Unusual price spikes
- New suppliers entering the market

### 4. **Share with Team**
Looker Studio dashboards can be shared via link (view/edit permissions)

### 5. **Mobile Access**
Dashboards work on mobile - check opportunities on the go!

---

## 📞 Next Steps

1. ✅ Connect Looker Studio to `analytics.super_tenders`
2. ✅ Build your first dashboard with filters
3. ✅ Share with your team
4. Schedule weekly data refreshes
5. Set up automated email reports

---

**Created:** 2025-01-07
**Database:** medical-473219:us-central1:pncp-medical-db
**Views:** 5 materialized views, 13,948 total rows
