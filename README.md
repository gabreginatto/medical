# PNCP Medical Data Processor

A comprehensive system for discovering, processing, and analyzing medical supply tenders from Brazil's Portal Nacional de Contratações Públicas (PNCP), with automated matching to Fernandes product catalog and competitive price analysis.

## 🆕 V8: Looker-First Approach

**New in V8:** Phase 3 (Product Matching) is now **OPTIONAL** for a better, more flexible workflow.

### 🎯 **The V8 Workflow**

**Problem V8 Solves:**
- V7 matched ALL items automatically with only 30% success rate (fuzzy matching)
- Wasted time on items you don't care about
- Hard to explore what products are actually available

**V8 Solution: Looker-First + AI Matching**

```
Step 1: Collect Data          Step 2: Explore           Step 3: AI Match
   (Automated)                   (Visual)                  (Targeted)
       ↓                           ↓                          ↓
   main.py              →    Looker Studio      →      ai_matching/
 (Phase 3 SKIP)              Find categories           70% success rate
   ~10 min                   Identify keywords           ~$0.02/run
```

### 📋 **Quick Start**

```bash
# 1. Daily data collection (Phase 3 skipped by default - faster!)
python3 main.py --start 20250101 --end 20250131 --states SP RJ

# 2. Explore in Looker Studio
# - Connect to Cloud SQL database
# - Run looker_views.sql to create 7 pre-built views
# - Create dashboards and find interesting product categories

# 3. Update keywords.json with products you want to match
# Example: ["curativo", "transparente", "filme", "gaze"]

# 4. Run AI matching for those specific products
python3 ai_matching/step1_extract_keywords.py  # Extract filtered items
python3 ai_matching/step2_gemini.py            # AI match (70% success)
python3 ai_matching/step3_save.py              # Save to database

# 5. View results in Looker
# Use vw_matched_products_analysis view

# Optional: Enable Phase 3 for automatic fuzzy matching (30% success)
python3 main.py --start 20250101 --end 20250131 --states SP --match
```

### 🎯 **V8 Benefits**

| Feature | V7 (Old) | V8 (New) |
|---------|----------|----------|
| Daily run time | ~15 min | ~10 min ⚡ |
| Phase 3 | Always runs | Skipped by default |
| Match quality | 30% (fuzzy) | 70% (AI) 🎯 |
| Flexibility | Match everything | Match what you want |
| Exploration | SQL queries | Visual dashboards 📊 |
| Cost | Free | ~$0.02 per category |
| Control | Automated | You decide what to match |

### 📊 **7 Pre-Built Looker Views**

Run `looker_views.sql` in your database to get:

1. **`vw_tender_items_complete`** - All items with full context
2. **`vw_curativos`** - Wound care products filter
3. **`vw_mdsap_items`** - MDSAP-relevant items filter
4. **`vw_high_value_items`** - High-value opportunities (>R$10k)
5. **`vw_items_by_state`** - Geographic aggregation
6. **`vw_matched_products_analysis`** - Match performance analysis
7. **`vw_monthly_trends`** - Time series analysis

### 🔄 **Recommended Schedule**

**Daily (Automated):**
```bash
# Cron job or Cloud Scheduler - runs every night
0 2 * * * python3 main.py --start $(date -d "yesterday" +%Y%m%d) --end $(date +%Y%m%d) --states SP RJ MG
```

**Weekly (15 min manual):**
1. Monday: Check Looker dashboards
2. Found interesting category? Update `keywords.json`
3. Run `ai_matching/` scripts
4. Review results in Looker

**Monthly (30 min manual):**
1. Review medium-confidence matches CSV
2. Update Fernandes catalog if needed
3. Re-run matching for updated products

### 📚 **Complete Documentation**

- **`V8_WORKFLOW.md`** - Detailed workflow guide with examples
- **`looker_views.sql`** - SQL views with usage instructions
- **`ai_matching/README.md`** - AI matching module guide
- **`LOOKER_STUDIO_GUIDE.md`** - Looker setup instructions

---

## 🎯 What This System Does

This system automatically:

1. **Discovers Medical Tenders** across all 27 Brazilian states
2. **Classifies Government Levels** (Federal/State/Municipal)
3. **Extracts Item-Level Homologated Prices** from completed tenders
4. **Matches Products** with your Fernandes catalog using advanced algorithms
5. **Analyzes Price Competitiveness** against FOB prices
6. **Prevents Duplicate Processing** with intelligent tracking (max 20 tenders per state per run)
7. **Stores Everything** in Google Cloud SQL for analysis
8. **Visualizes with Looker Studio** for live business intelligence dashboards
9. **Generates Reports** for business intelligence

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   PNCP API     │ -> │  Classification  │ -> │  Product Match  │
│   (Tenders)    │    │  Engine          │    │  Engine         │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │                       │
                                v                       v
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ Looker Studio   │ <- │  Google Cloud    │ <- │  Price Analysis │
│   Dashboard     │    │  SQL Database    │    │  Engine         │
└─────────────────┘    └──────────────────┘    └─────────────────┘
        ^                        │                       │
        │                        v                       v
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Duplicate     │    │   Processing     │    │   Reports &     │
│   Prevention    │    │   Tracker        │    │   Analytics     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## 🚀 Quick Start

### 1. Prerequisites

- Python 3.9+
- Google Cloud Project with Cloud SQL
- Fernandes product catalog

**Note:** PNCP API credentials are NOT required - the Consultation API is public and does not require authentication.

### 2. Installation

```bash
# Clone repository
git clone https://github.com/gabreginatto/medical.git
cd medical

# Install dependencies
pip install -r requirements.txt

# Install additional Cloud SQL dependencies
pip install asyncpg google-cloud-sql-connector
```

### 3. Environment Configuration

Create a `.env` file:

```env
# Google Cloud Configuration
GOOGLE_CLOUD_PROJECT=medical-473219
CLOUD_SQL_REGION=us-central1
CLOUD_SQL_INSTANCE=pncp-medical-db
DATABASE_NAME=pncp_medical_data
USE_PRIVATE_IP=false

# Optional: Product catalog
FERNANDES_CATALOG_CSV=path/to/fernandes_catalog.csv
```

### 4. Database Setup

**Option A: Automated Setup (Recommended)**
```bash
# Complete automated database setup
python complete_db_setup.py
```

This will:
- ✅ Wait for Cloud SQL instance to be ready
- ✅ Create the database `pncp_medical_data`
- ✅ Set up IAM authentication
- ✅ Initialize database schema
- ✅ Test connection

**Option B: Manual Setup**
```bash
# If automated setup fails, use the generated schema file
gcloud sql connect your-instance-name --user=postgres
# Then in psql: \c pncp_medical_data
# Execute the contents of schema.sql
```

### 5. Run Processing

```bash
# Process tenders for specific date range and states (20 tenders per state max)
python main.py --start-date 20240101 --end-date 20240131 --states DF SP

# Discovery only (no item processing)
python main.py --start-date 20240101 --end-date 20240131 --discovery-only

# Process items for already discovered tenders
python main.py --items-only

# View processing statistics and progress
python view_processed_tenders.py
```

## 📁 Project Structure

```
pncp-medical-processor/
├── config.py                    # Configuration and constants
├── database.py                  # Cloud SQL database operations
├── pncp_api.py                  # PNCP API client with auth
├── classifier.py                # Tender classification system
├── product_matcher.py           # Product matching algorithms
├── tender_discovery.py          # Tender discovery engine
├── item_processor.py            # Item processing and price extraction
├── main.py                      # Main orchestration
├── complete_db_setup.py         # Automated Cloud SQL database setup
├── schema.sql                   # Database schema definition
├── processed_tenders_tracker.py # Duplicate prevention system
├── view_processed_tenders.py    # Processing statistics viewer
├── requirements.txt             # Python dependencies
├── README.md                    # This file
├── LOOKER_STUDIO_GUIDE.md      # Looker Studio dashboard guide
├── processed_tenders.json       # Processed tenders tracking (auto-generated)
└── exports/                     # Generated reports and exports
```

## ⚙️ Configuration Options

### State Selection
```python
# Process specific states
enabled_states = ['DF', 'SP', 'RJ', 'MG']

# Process all states (default)
enabled_states = list(BRAZILIAN_STATES.keys())
```

### Government Level Filtering
```python
government_levels = [
    GovernmentLevel.FEDERAL,
    GovernmentLevel.STATE,
    GovernmentLevel.MUNICIPAL
]
```

### Tender Value Filtering
```python
min_tender_value = 10_000.0    # Minimum R$10k
max_tender_value = 5_000_000.0 # Maximum R$5M
```

### Product Matching
```python
min_match_score = 50.0  # Minimum 50% similarity
dimension_tolerance = 0.2  # ±20% size tolerance
```

## ✨ Key Features

### 1. **Intelligent Duplicate Prevention**
- **Tracks processed tenders** in `processed_tenders.json`
- **Never processes the same tender twice** across multiple runs
- **Scales efficiently** - processes 20 highest-value tenders per state per run
- **Smart resumption** - can restart and continue where it left off
- **Progress tracking** - view statistics with `python view_processed_tenders.py`

### 2. **Live Looker Studio Dashboard Integration**
- **Real-time visualization** - connect directly to Cloud SQL database
- **Interactive dashboards** - explore tenders, items, and competitive opportunities
- **Business intelligence** - visual analytics with filters and drill-downs
- **Mobile access** - check opportunities on your phone
- **See LOOKER_STUDIO_GUIDE.md** for setup instructions

### 3. **Smart Classification**
- **Government Level**: Automatically identifies Federal/State/Municipal tenders
- **Organization Type**: Hospital, Health Secretariat, University, etc.
- **Tender Size**: Small (<R$50k), Medium, Large, Mega (>R$5M)
- **Medical Relevance**: Filters for medical supply tenders

### 4. Advanced Product Matching
- **Keyword Matching**: Medical terminology in Portuguese/English
- **Fuzzy String Matching**: Handles typos and variations
- **Dimensional Matching**: Size matching with ±20% tolerance
- **Composite Scoring**: Weighted combination of all factors

### 5. Price Analysis
- **Homologated vs FOB Comparison**: Calculates markup percentages
- **Competitive Analysis**: Identifies opportunities
- **Currency Conversion**: USD/BRL exchange rate handling
- **Volume Analysis**: MOQ vs tender quantities

### 6. Comprehensive Database Schema
```sql
-- Key tables
organizations       -- Government entities
tenders            -- Tender information
tender_items       -- Individual items
matched_products   -- Product matches
homologated_results -- Detailed bid results
processing_log     -- Audit trail
```

## ⚡ Processing Efficiency

### **Intelligent Scaling**
```bash
# First run - processes 20 highest-value tenders per state
python main.py --start-date 20240101 --end-date 20240131 --states SP RJ
# Result: SP=20 tenders, RJ=20 tenders (40 total)

# Second run - processes NEXT 20 highest-value unprocessed tenders per state
python main.py --start-date 20240101 --end-date 20240131 --states SP RJ
# Result: SP=20 NEW tenders, RJ=20 NEW tenders (40 total, 80 cumulative)

# Third run - continues with next batch
python main.py --start-date 20240101 --end-date 20240131 --states SP RJ
# Result: Continues processing without duplicating previous work
```

### **Progress Tracking**
```bash
# View what's been processed anytime
python view_processed_tenders.py

# Sample output:
📊 PROCESSED TENDERS STATISTICS
==================================================
Total Processed: 180
Total Value: R$24,750,000.00
Total Items: 4,250
Total Matches: 1,580

By State:
  SP: 80 tenders
  RJ: 60 tenders
  DF: 40 tenders
```

## 📊 Sample Output

### Discovery Statistics
```
=== TENDER DISCOVERY STATISTICS ===
Total Tenders Found: 15,247
Medical Relevant: 3,891
Processing Time: 245.3 seconds

--- By State ---
São Paulo (SP): 5,234
Rio de Janeiro (RJ): 2,187
Federal District (DF): 1,543
Minas Gerais (MG): 1,429

--- By Government Level ---
Municipal: 2,156
State: 1,234
Federal: 501
```

### Product Matching Results
```
Tender Item: CURATIVO TRANSPARENTE FENESTRADO 5X7CM
Best Match: IVFS.5057 - CURATIVO IV TRANSP. FENESTRADO COM BORDA - 5X5-7CM
Match Score: 87.3%
Homologated Price: R$0.45
FOB Price: $0.074 (R$0.37)
Price Difference: +21.6%
Status: ✅ Competitive
```

## 🔧 API Rate Limiting

The system includes intelligent rate limiting:
- **60 requests/minute** (default)
- **1000 requests/hour** (default)
- **Automatic backoff** on 429 responses
- **Concurrent processing** with semaphores

## 🛠️ Advanced Usage

### Custom Configuration
```python
config = ProcessingConfig(
    enabled_states=['SP', 'RJ'],
    min_tender_value=50000.0,
    allowed_modalities=[6, 8],  # Pregão Eletrônico, Dispensa
    min_match_score=60.0
)

processor = PNCPMedicalProcessor(config)
```

### Batch Processing by Date Chunks
```python
# Process large date ranges in chunks
await processor.discover_tenders(
    '20230101', '20231231',
    chunk_days=7  # Process week by week
)
```

### Export Data
```python
# Export to CSV
await processor.export_data_to_csv('exports/')

# Generate reports
await processor.generate_reports(discovery_stats, item_results)
```

## 🐛 Troubleshooting

### Common Issues

1. **API Connection Error**
   ```
   Error: Failed to connect to PNCP API
   ```
   - Check your internet connection
   - Verify the PNCP API is accessible (https://pncp.gov.br/api/consulta)
   - Check if there are any firewall restrictions

2. **Database Connection Error**
   ```
   Error: Failed to connect to Cloud SQL instance
   ```
   - Verify GOOGLE_CLOUD_PROJECT and instance settings
   - Check IAM permissions for Cloud SQL
   - Ensure instance is running

3. **Rate Limiting**
   ```
   Warning: Rate limit reached, sleeping for 30.2 seconds
   ```
   - This is normal - system will automatically handle it
   - Reduce concurrent processing if needed

4. **No Medical Tenders Found**
   - Check date range (recent tenders more likely)
   - Verify state codes are correct
   - Lower min_match_score threshold

### Debugging

Enable debug logging:
```python
import logging
logging.getLogger().setLevel(logging.DEBUG)
```

Check processing logs:
```bash
tail -f pncp_processing.log
```

## 📈 Performance

### Typical Performance Metrics
- **Discovery Rate**: ~500 tenders/minute
- **Item Processing**: ~50 items/minute
- **Match Processing**: ~1000 items/minute
- **Database Storage**: ~100 records/second

### Optimization Tips
- Use chunked date processing for large ranges
- Process states in parallel when possible
- Increase `max_concurrent` for faster processing
- Use database batching for bulk inserts

## 🤝 Contributing

### Development Setup
```bash
pip install -r requirements.txt
pip install pytest black flake8

# Run tests
pytest tests/

# Format code
black *.py

# Lint
flake8 *.py
```

### Adding New Features
1. Fork the repository
2. Create feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit pull request

## 📄 License

This project is proprietary software for Fernandes Medical Supply Analysis.

## 🆘 Support

For issues and questions:
1. Check troubleshooting section
2. Review logs in `pncp_processing.log`
3. Contact development team

---

## 🔄 Version History

### V1 (September 2025)
**Current Status: Development & Testing Phase**

✅ **Completed:**
- PNCP API integration with public consultation endpoints (no authentication required)
- Google Cloud SQL database setup with IAM authentication
- Complete database schema with 6 core tables
- Tender classification system (government level, organization type, medical relevance)
- Rate limiting and error handling for API requests
- Product matching framework
- Test infrastructure (`tests/test_sp_process.py`)

🚧 **In Progress:**
- Fine-tuning medical relevance classifier thresholds
- Testing with real São Paulo state tender data
- Optimizing query parameters for completed tenders discovery

📋 **Known Issues:**
- Need to expand tender discovery limits to find medical-relevant tenders
- API returns many non-medical tenders requiring filtering
- Session cleanup warnings in async operations (non-critical)

**Next Steps:**
1. Expand tender discovery to larger sample sizes (500-1000 tenders)
2. Test across multiple modalities (Pregão Eletrônico, Dispensa)
3. Validate product matching accuracy
4. Begin price competitiveness analysis testing
5. Set up Looker Studio dashboards for visualization (see LOOKER_STUDIO_GUIDE.md)

**Technical Details:**
- Database: Cloud SQL PostgreSQL (us-central1)
- API: PNCP Consultation API (public, no auth)
- Language: Python 3.9+ with async/await
- Key Libraries: aiohttp, asyncpg, google-cloud-sql-connector

---

**Built for competitive intelligence in Brazilian medical supply markets** 🇧🇷

Last updated: September 2025