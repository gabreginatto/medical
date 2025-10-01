# Backup - Legacy Files

This folder contains files from V1 that have been replaced by the V2 optimized system.

## 📁 Folder Structure

### `v1_legacy/`
Legacy V1 system files replaced by V2 optimized discovery:

- **main.py** - Old orchestration using tender_discovery.py
  - **Replaced by:** `example_optimized_discovery.py` + `optimized_discovery.py`
  - **Reason:** V1 used 2-stage discovery; V2 uses 4-stage with 96% less API calls

- **tender_discovery.py** - Old discovery engine
  - **Replaced by:** `optimized_discovery.py`
  - **Improvements in V2:**
    - 4-stage progressive filtering (was 2-stage)
    - Stage 2 quick filter (0 API calls)
    - Stage 3 smart sampling (3 items vs all)
    - Priority-based processing
    - 89% faster, 96% fewer API calls

- **processed_tenders_tracker.py** - Old tracking system
  - **Replaced by:** `org_cache.py` (multi-level caching)
  - **Improvements in V2:**
    - Organization + tender + item caching
    - TTL-based expiration
    - Persistent JSON storage
    - Pre-loaded seed data

- **view_processed_tenders.py** - Old utility for viewing tenders
  - **Replaced by:** `analytics.py` (comprehensive analytics)
  - **Improvements in V2:**
    - Performance tracking
    - Medical procurement insights
    - Top equipment/buyers analysis
    - Monthly trends
    - JSON export

### `old_setup_scripts/`
Setup scripts replaced by V2 database migration:

- **complete_db_setup.py** - Old database initialization
  - **Replaced by:** `setup/database_migration_catmat.sql`
  - **Improvements in V2:**
    - CATMAT tracking columns
    - Materialized views
    - Performance indexes
    - Comprehensive migration with rollback

- **setup_notion_databases.py** - Old Notion setup
  - **Status:** Still functional, but integrated into V2 workflow

- **schema.sql** - Old database schema
  - **Replaced by:** `setup/database_migration_catmat.sql`
  - **Improvements in V2:**
    - Enhanced schema with CATMAT support
    - Materialized views for performance
    - Helper views for analytics
    - Performance tracking table

## 🔄 Migration Notes

If you need to restore V1 functionality:

```bash
# Switch to V1 branch (if it exists)
git checkout V1

# Or copy files back to root
cp backup/v1_legacy/main.py .
cp backup/v1_legacy/tender_discovery.py .
```

## 📊 V1 vs V2 Comparison

| Feature | V1 (Legacy) | V2 (Current) |
|---------|-------------|--------------|
| **Discovery Stages** | 2 (fetch + classify) | 4 (fetch + quick filter + sample + process) |
| **API Calls** | ~5000 per 1000 tenders | ~350 per 1000 tenders |
| **Processing Time** | ~45 minutes | ~5 minutes |
| **Medical Precision** | ~70% | ~85%+ |
| **Caching** | Basic tracking | Multi-level (org + tender + items) |
| **CATMAT Support** | Basic keywords | Full post-processing pipeline |
| **Analytics** | Basic logging | Comprehensive reports + insights |
| **Performance Monitoring** | None | Stage-by-stage metrics |

## 🗓️ Archived Date
**Date:** 2025-01-XX (V2 Release)
**Branch:** V2
**Commit:** 3e75e3e

## ⚠️ Important Notes

- These files are kept for reference only
- V2 system is production-ready and recommended
- V1 files may have outdated dependencies
- Database schema may not be compatible with V1 after V2 migration

---

**For V2 documentation, see:**
- `Docs/IMPLEMENTATION_GUIDE.md` - Complete usage guide
- `Docs/ENHANCEMENTS_SUMMARY.md` - Technical overview
- `example_optimized_discovery.py` - Working examples
