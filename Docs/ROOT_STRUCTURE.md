# Root Directory Structure - V2 System

## 📁 Clean Root Directory (Active Files Only)

### 🚀 **V2 Core System Files**

#### **Discovery & Processing**
- `optimized_discovery.py` - 4-stage progressive filtering pipeline
- `classifier.py` - Medical classification with CATMAT + enhanced keywords
- `pncp_api.py` - PNCP API client with sample fetching
- `item_processor.py` - Item processing with CATMAT detection
- `org_cache.py` - Multi-level caching (org + tender + items)

#### **Analytics & Insights**
- `analytics.py` - Performance tracking & procurement analytics

#### **Supporting Components**
- `database.py` - Cloud SQL operations
- `config.py` - System configuration with CATMAT options
- `product_matcher.py` - Fernandes product matching
- `notion_integration.py` - Notion export

#### **Examples & Testing**
- `example_optimized_discovery.py` - 5 ready-to-run usage examples

### 📋 **Configuration Files**
- `.env` - Environment variables (credentials)
- `.env.example` - Environment template
- `.gitignore` - Git ignore rules
- `requirements.txt` - Python dependencies
- `pncp-key.json` - Service account key

### 📚 **Documentation**
- `README.md` - Project overview
- `Docs/` - Complete documentation
  - `IMPLEMENTATION_GUIDE.md` - Usage guide
  - `ENHANCEMENTS_SUMMARY.md` - Technical overview
  - `NOTION_SETUP.md` - Notion integration
  - API documentation PDFs

### 🔧 **Setup & Migration**
- `setup/` - Database setup scripts
  - `database_migration_catmat.sql` - V2 schema migration
  - Other initialization scripts

### 🧪 **Tests**
- `tests/` - Test files
  - `test_api_access.py`
  - `test_sp_process.py`
  - `verify_setup.py`

### 🗃️ **Archived Files**
- `backup/` - V1 legacy files (not used by V2)
  - `v1_legacy/` - Old system files
    - `main.py` (replaced by example_optimized_discovery.py)
    - `tender_discovery.py` (replaced by optimized_discovery.py)
    - `processed_tenders_tracker.py` (replaced by org_cache.py)
    - `view_processed_tenders.py` (replaced by analytics.py)
  - `old_setup_scripts/` - Old setup files
    - `complete_db_setup.py`
    - `schema.sql` (replaced by database_migration_catmat.sql)
    - `setup_notion_databases.py`
  - `README.md` - Backup documentation

---

## 🎯 Quick Start (V2)

### 1. Run Database Migration
```bash
psql -f setup/database_migration_catmat.sql
```

### 2. Run Example Discovery
```bash
python example_optimized_discovery.py
# Select option 1-6
```

### 3. View Analytics
```python
from analytics import MedicalProcurementAnalytics
# See example_optimized_discovery.py for full usage
```

---

## 📊 File Count Summary

| Category | Count | Size |
|----------|-------|------|
| **Active Python Files** | 11 | Core system |
| **Configuration Files** | 4 | .env, .gitignore, requirements.txt, keys |
| **Documentation** | 3+ | README + Docs folder |
| **Setup Scripts** | 1 | database_migration_catmat.sql |
| **Test Files** | 3 | tests/ folder |
| **Archived Files** | 7 | backup/ folder |

---

## 🔄 V1 → V2 Migration Map

| V1 File (Archived) | V2 Replacement | Location |
|-------------------|----------------|----------|
| `main.py` | `example_optimized_discovery.py` | Root |
| `tender_discovery.py` | `optimized_discovery.py` | Root |
| `processed_tenders_tracker.py` | `org_cache.py` | Root |
| `view_processed_tenders.py` | `analytics.py` | Root |
| `schema.sql` | `database_migration_catmat.sql` | setup/ |
| `complete_db_setup.py` | Migration SQL | setup/ |

---

## 🗂️ Folder Structure
```
Medical/
├── 📄 Python Files (11 active)
│   ├── optimized_discovery.py  ⭐ V2 Core
│   ├── analytics.py             ⭐ V2 Analytics
│   ├── org_cache.py             ⭐ V2 Caching
│   ├── classifier.py            ✨ Enhanced
│   ├── config.py                ✨ Enhanced
│   ├── pncp_api.py              ✨ Enhanced
│   ├── item_processor.py        ✨ Enhanced
│   ├── database.py
│   ├── product_matcher.py
│   ├── notion_integration.py
│   └── example_optimized_discovery.py
│
├── 📁 Docs/
│   ├── IMPLEMENTATION_GUIDE.md  ⭐ V2 Guide
│   ├── ENHANCEMENTS_SUMMARY.md  ⭐ V2 Overview
│   ├── NOTION_SETUP.md
│   └── API Docs/
│
├── 📁 setup/
│   └── database_migration_catmat.sql  ⭐ V2 Migration
│
├── 📁 tests/
│   ├── test_api_access.py
│   ├── test_sp_process.py
│   └── verify_setup.py
│
├── 📁 backup/  🗃️ V1 Legacy
│   ├── README.md
│   ├── v1_legacy/
│   └── old_setup_scripts/
│
├── 📄 Config Files
│   ├── .env
│   ├── .env.example
│   ├── .gitignore
│   ├── requirements.txt
│   ├── pncp-key.json
│   └── README.md
│
└── 📁 .git/
```

---

## ✅ What Changed

### Removed from Root (Moved to `backup/`)
- ❌ `main.py` - Old V1 orchestration
- ❌ `tender_discovery.py` - Old 2-stage discovery
- ❌ `processed_tenders_tracker.py` - Old tracking
- ❌ `view_processed_tenders.py` - Old viewer
- ❌ `complete_db_setup.py` - Old setup
- ❌ `setup_notion_databases.py` - Old Notion setup
- ❌ `schema.sql` - Old schema

### Added to Root (V2 System)
- ✅ `optimized_discovery.py` - 4-stage pipeline
- ✅ `analytics.py` - Analytics engine
- ✅ `org_cache.py` - Multi-level caching
- ✅ `example_optimized_discovery.py` - Examples

### Enhanced in Root
- ✨ `classifier.py` - Added quick_medical_score() + CATMAT
- ✨ `config.py` - Added municipality + CATMAT options
- ✨ `pncp_api.py` - Added fetch_sample_items()
- ✨ `item_processor.py` - Added CATMAT detection

---

## 📈 Benefits of Clean Structure

1. **Clarity** - Only active V2 files in root
2. **Performance** - No confusion between V1/V2
3. **Maintenance** - Easy to identify core system files
4. **Documentation** - Clear migration path in backup/
5. **Onboarding** - New developers see only active code

---

**Last Updated:** 2025-01-XX
**Version:** V2
**Status:** ✅ Production Ready
