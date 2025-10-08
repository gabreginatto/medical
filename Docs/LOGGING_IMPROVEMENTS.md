# Logging Improvements for PNCP Medical Data Processing

## Problem Identified

**Current Issue:** After "Stage 4 complete: 702 tenders fully processed", there's no logging output visible in the log file for Phase 2 (Fetching Tender Items), even though the process is still running.

**Root Cause:** The `fetch_and_save_items.py` module uses `print()` statements instead of `logger.info()`, which means:
- Output goes to **stdout** (terminal) only
- Output does **NOT** appear in the log file
- Makes monitoring batch runs impossible without watching the terminal

---

## Files Requiring Changes

### 1. **fetch_and_save_items.py**
**Current:** Uses `print()` statements
**Issue:** No logging to file during Phase 2
**Impact:** Cannot track progress for 702 tenders being processed

### 2. **match_tender_items.py** (likely same issue)
**Current:** Probably also uses `print()` statements
**Issue:** No logging to file during Phase 3

### 3. **notion_integration.py** (if exists)
**Current:** Probably also uses `print()` statements
**Issue:** No logging to file during Phase 4

---

## Recommended Changes

### Change 1: Replace all `print()` with `logger.info()` in fetch_and_save_items.py

**Lines to change:**
```python
# Line ~26-27: Change from:
print("=" * 70)
print("📦 FETCH AND SAVE TENDER ITEMS")
print("=" * 70)

# To:
logger.info("=" * 70)
logger.info("📦 FETCH AND SAVE TENDER ITEMS")
logger.info("=" * 70)

# Line ~34: Change from:
print("\n1️⃣  Initializing...")

# To:
logger.info("1️⃣  Initializing...")

# Line ~40: Change from:
print("   ✅ Initialized")

# To:
logger.info("✅ Initialized")

# Line ~43: Change from:
print("\n2️⃣  Fetching unprocessed tenders from database...")

# To:
logger.info("2️⃣  Fetching unprocessed tenders from database...")

# Line ~45: Change from:
print(f"   ✅ Found {len(tenders)} tenders without items")

# To:
logger.info(f"✅ Found {len(tenders)} tenders without items")

# Line ~48: Change from:
print("\n3️⃣  Fetching items from PNCP API...")

# To:
logger.info("3️⃣  Fetching items from PNCP API...")

# Line ~90: Change from:
print(f"   Progress: {i}/{len(tenders)} tenders processed...")

# To:
logger.info(f"Progress: {i}/{len(tenders)} tenders processed...")

# Line ~152: Change from:
print(f"   Progress: {i}/{len(tenders)} tenders, {total_items} items saved...")

# To:
logger.info(f"Progress: {i}/{len(tenders)} tenders, {total_items} items saved...")

# Lines ~159-175: Change all remaining print() to logger.info()
```

**Add at top of file:**
```python
import logging
logger = logging.getLogger(__name__)
```

---

### Change 2: Add more detailed progress logging

**Add periodic detailed progress:**

```python
# Inside the main processing loop (around line 90-152):

# Every 10 tenders, log detailed progress
if i % 10 == 0 and i > 0:
    elapsed = (datetime.now() - start_time).total_seconds()
    rate = i / elapsed if elapsed > 0 else 0
    remaining = len(tenders) - i
    eta = remaining / rate if rate > 0 else 0

    logger.info(f"Progress: {i}/{len(tenders)} tenders ({i/len(tenders)*100:.1f}%) | "
                f"Items: {total_items} | "
                f"Rate: {rate:.1f} tenders/sec | "
                f"ETA: {eta/60:.1f} min")

# Every 50 tenders, log summary stats
if i % 50 == 0 and i > 0:
    logger.info(f"📊 Checkpoint - With items: {tenders_with_items}, "
                f"Without items: {tenders_without_items}, "
                f"Failed: {failed_tenders}")
```

---

### Change 3: Add transition logging in main.py

**After line 267 in main.py (await self.fetch_items()):**

```python
# Before calling fetch_items():
logger.info("Starting item fetch for discovered tenders...")
logger.info(f"Expected tenders to process: {discovery_metrics.stage4_full_processing.tenders_out}")

await self.fetch_items()

# After fetch_items() completes:
logger.info("Item fetch completed, proceeding to product matching...")
```

---

### Change 4: Add database save logging

**In database.py or wherever items are saved, add:**

```python
# When saving items in batches:
logger.info(f"Saving batch of {len(items)} items to database...")

# After successful save:
logger.info(f"✅ Saved {len(items)} items successfully")

# On error:
logger.error(f"❌ Failed to save items: {error}")
```

---

## Expected Output After Changes

**Phase 1 (Discovery) - Already Good:**
```
PHASE 1: TENDER DISCOVERY
🔍 Stage 1 complete: 5396 tenders fetched
🔍 Stage 2 complete: 797 tenders retained (85.2% filtered out)
🎯 Stage 3 complete: 702 tenders confirmed via sampling (11.9% filtered out)
⚡ Stage 4 complete: 702 tenders fully processed
```

**Phase 2 (Fetching Items) - Currently Missing:**
```
PHASE 2: FETCHING TENDER ITEMS
1️⃣  Initializing...
✅ Initialized
2️⃣  Fetching unprocessed tenders from database...
✅ Found 702 tenders without items
3️⃣  Fetching items from PNCP API...
Progress: 10/702 tenders (1.4%) | Items: 45 | Rate: 0.5 tenders/sec | ETA: 23.1 min
Progress: 20/702 tenders (2.8%) | Items: 92 | Rate: 0.6 tenders/sec | ETA: 19.0 min
...
📊 Checkpoint - With items: 45, Without items: 5, Failed: 0
...
Progress: 702/702 tenders (100.0%) | Items: 3241 | Rate: 0.7 tenders/sec
✅ Item fetching complete

📊 SUMMARY
Total Tenders Processed: 702
Tenders with Items: 680
Tenders without Items: 18
Failed Tenders: 4
Total Items Saved: 3241
Average Items per Tender: 4.8
```

---

## Implementation Steps

**IMPORTANT: Do NOT implement while batch is running!**

1. **Wait for current batch to complete**
2. **Create backup:**
   ```bash
   cp fetch_and_save_items.py fetch_and_save_items.py.backup
   cp match_tender_items.py match_tender_items.py.backup
   cp main.py main.py.backup
   ```

3. **Apply changes in order:**
   - First: `fetch_and_save_items.py` (highest priority)
   - Second: `match_tender_items.py`
   - Third: `notion_integration.py` (if exists)
   - Fourth: `main.py` transition logging

4. **Test with single month:**
   ```bash
   python3 main.py --start-date 20250201 --end-date 20250228 --states SP
   ```

5. **Verify logging works:**
   ```bash
   tail -f logs/pncp_run_full_*.log
   ```

6. **If successful, run full batch:**
   ```bash
   python3 run_monthly_batches.py --state SP --start 2025-02 --months 6
   ```

---

## Additional Improvements (Optional)

### Add Real-time Progress Bar (if running interactively)
```python
from tqdm import tqdm

for i, tender in enumerate(tqdm(tenders, desc="Fetching items")):
    # ... process tender
    logger.info(f"Processing tender {i+1}/{len(tenders)}")
```

### Add Memory Usage Logging
```python
import psutil
import os

process = psutil.Process(os.getpid())
memory_mb = process.memory_info().rss / 1024 / 1024
logger.info(f"Memory usage: {memory_mb:.1f} MB")
```

### Add Error Rate Monitoring
```python
error_rate = failed_tenders / (i + 1) * 100
if error_rate > 10:
    logger.warning(f"⚠️  High error rate detected: {error_rate:.1f}%")
```

---

## Priority Level

**CRITICAL** - Without this, batch processing cannot be monitored effectively via log files. Current workaround is to watch terminal output, which is not feasible for long-running batch jobs.

**Estimated Impact:**
- Development time: 30 minutes
- Testing time: 15 minutes
- Total: 45 minutes
- Risk: LOW (only changing print to logger, no logic changes)
- Benefit: HIGH (essential for production monitoring)
