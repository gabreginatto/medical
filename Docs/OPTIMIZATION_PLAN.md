# PNCP Medical Tender Discovery - Optimization Plan

## Current Performance Baseline (V5)

**Test Configuration:**
- Date Range: Jul 1 - Sep 15, 2024 (75 days)
- State: São Paulo (SP)
- Modalities: [1, 6, 9, 12] (optimized in V5)
- Max Tenders: 5,000

**Results:**
- **Total Duration:** 56 minutes
- **Stage 1 (Bulk Fetch):** 34 minutes - **PRIMARY BOTTLENECK**
- **Stage 3 (Sampling):** 22 minutes - **ELIMINATED in V5**
- **Tenders Fetched:** 3,940 (78.8% of target)
- **Medical Tenders:** 391
- **API Calls:** ~571 total

**Key Bottleneck Identified:**
- Stage 1 takes 60% of total time (34/56 minutes)
- Sequential page fetching at ~6 API calls/minute
- API rate limit: 60 req/min, 1000 req/hour per IP

---

## Optimization Strategies (Ranked by Impact)

### 🥇 **Strategy 1: Multi-IP Parallel Fetching** (HIGHEST IMPACT)

**Problem:** Single IP limited to 60 req/min, sequential processing
**Solution:** Deploy multiple workers with different IPs to parallelize Stage 1

**Architecture:**
```
┌─────────────────────────────────────────────────┐
│          Coordinator (Main Process)              │
│  - Splits date range into chunks                │
│  - Distributes work to workers                  │
│  - Aggregates results                           │
└────────────┬────────────────────────────────────┘
             │
     ┌───────┴───────┬────────────┬──────────┐
     │               │            │          │
┌────▼────┐    ┌────▼────┐  ┌────▼────┐  ┌──▼──────┐
│Worker 1 │    │Worker 2 │  │Worker 3 │  │Worker N │
│ IP #1   │    │ IP #2   │  │ IP #3   │  │ IP #N   │
│ Pages   │    │ Pages   │  │ Pages   │  │ Pages   │
│ 1-50    │    │ 51-100  │  │101-150  │  │151-200  │
└─────────┘    └─────────┘  └─────────┘  └─────────┘
```

**Implementation Options:**

#### Option 1A: Multiple GCP Cloud Run Instances
- ✅ Easy deployment, auto-scaling
- ✅ Different IPs per instance
- ✅ Pay-per-use pricing
- ⚠️  Requires coordination layer
- **Cost:** ~$5-10/month for 4-8 workers
- **Speedup:** 4-8x (34 min → 4-8 min)

#### Option 1B: AWS Lambda Functions
- ✅ Serverless, different IPs
- ✅ 1000 concurrent executions possible
- ✅ Very cheap ($0.20 per 1M requests)
- ⚠️  15-minute timeout (need chunking)
- **Cost:** <$1/month for typical usage
- **Speedup:** 8-16x (34 min → 2-4 min)

#### Option 1C: Residential Proxy Service
- ✅ Rotating IPs, unlimited
- ✅ No infrastructure needed
- ❌ Monthly cost ($50-200/month)
- ⚠️  May violate PNCP terms of service
- **Cost:** $50-200/month
- **Speedup:** 10-20x (34 min → 2-3 min)

#### Option 1D: Multiple VPS/Droplets
- ✅ Full control, persistent
- ✅ Each has unique IP
- ⚠️  Manual setup & management
- **Cost:** $20-40/month (4-8 servers)
- **Speedup:** 4-8x (34 min → 4-8 min)

**Recommended:** Option 1B (AWS Lambda) for best cost/performance

---
1
### 🥈 **Strategy 2: Smart Date Range Chunking** (MEDIUM IMPACT)

**Problem:** Fetching 75 days at once takes too long
**Solution:** Split into smaller date chunks and process in parallel

**Current:**
```
[Jul 1 ─────────────────────── Sep 15] = 34 minutes
```

**Optimized:**
```
[Jul 1 ─ Jul 25]  ┐
[Jul 26 ─ Aug 20] ├─ Parallel → 11-17 minutes
[Aug 21 ─ Sep 15] ┘
```

**Benefits:**
- Each chunk completes faster (less pagination)
- Can run in parallel with different workers
- Better error recovery (fail one chunk, not all)
- **Speedup:** 2-3x alone, 6-12x combined with Strategy 1

**Implementation:**
```python
def chunk_date_range(start_date, end_date, days_per_chunk=25):
    """Split date range into optimal chunks"""
    chunks = []
    current = start_date
    while current < end_date:
        chunk_end = min(current + timedelta(days=days_per_chunk), end_date)
        chunks.append((current, chunk_end))
        current = chunk_end
    return chunks

# Distribute chunks to workers
chunks = chunk_date_range(start_date, end_date, days_per_chunk=25)
# Each worker processes one chunk in parallel
```

---

### 🥉 **Strategy 3: Incremental Caching System** (LONG-TERM IMPACT)

**Problem:** Re-fetching the same tenders every run
**Solution:** Cache tenders, only fetch new/changed ones

**Architecture:**
```
┌──────────────────────────────────────┐
│   Cache Layer (Redis/PostgreSQL)    │
│  - Store fetched tenders by date    │
│  - Track last update time            │
│  - Only fetch delta                  │
└──────────────────────────────────────┘
```

**Implementation:**
```python
class TenderCache:
    def __init__(self):
        self.cache = {}  # or Redis

    def get_last_fetch_date(self, state, modality):
        """Get last successful fetch date"""
        pass

    def fetch_incremental(self, state, modality, last_date, today):
        """Only fetch tenders published since last run"""
        # First run: fetch 75 days (34 minutes)
        # Daily runs: fetch 1 day (<2 minutes)
        pass
```

**Benefits:**
- **First run:** Same time as current (34 min)
- **Daily runs:** 1-5 minutes (only new tenders)
- **Weekly runs:** 5-10 minutes
- Reduces API load dramatically

---

### 🎯 **Strategy 4: Modality Prioritization** (QUICK WIN)

**Problem:** Equal priority for all modalities
**Solution:** Fetch high-volume modalities first

**Current:** Process modalities sequentially: [1, 6, 9, 12]
**Optimized:** Prioritize by volume and medical relevance

```python
MODALITY_PRIORITY = {
    6: 1,   # Pregão Eletrônico - HIGHEST (80% of tenders)
    12: 2,  # Registro de Preços - HIGH
    1: 3,   # Concorrência - MEDIUM
    9: 4,   # Inexigibilidade - LOW volume
}
```

**Benefits:**
- Get results faster (most medical tenders found early)
- Can stop early if time-limited
- Better resource allocation

---

### 🔧 **Strategy 5: Async Concurrency Within Single IP** (EASY WIN)

**Problem:** Sequential page fetching even within single IP
**Solution:** Concurrent requests within rate limit

**Current:**
```python
# Sequential - 1 request at a time
for page in range(1, 250):
    await fetch_page(page)  # Wait for each
```

**Optimized:**
```python
# Concurrent - 10 requests at a time (within 60/min limit)
import asyncio

async def fetch_with_semaphore(page, semaphore):
    async with semaphore:
        return await fetch_page(page)

semaphore = asyncio.Semaphore(10)  # 10 concurrent requests
tasks = [fetch_with_semaphore(page, semaphore)
         for page in range(1, 250)]
results = await asyncio.gather(*tasks)
```

**Benefits:**
- Use full rate limit capacity (60 req/min)
- 2-3x speedup within single IP
- **Easy to implement** - just adjust existing code
- **Speedup:** 2-3x (34 min → 11-17 min)

---

### 📊 **Strategy 6: Smarter Modality Selection** (DONE IN V5 ✅)

**Problem:** Modality 8 (Dispensa) wasted 374 API calls
**Solution:** Remove modalities with poor item availability

**V4:** [6, 8] → 374 wasted sampling calls
**V5:** [1, 6, 9, 12] → Eliminated 374 calls (22 minutes saved)

**Status:** ✅ **IMPLEMENTED**

---

## Combined Optimization Scenarios

### Scenario A: "Quick Wins" (Easiest Implementation)
**Strategies:** 5 (Async Concurrency) + 4 (Prioritization)
**Effort:** 2-3 days
**Speedup:** 2-3x
**New Duration:** 15-20 minutes
**Cost:** $0 (no infrastructure)

### Scenario B: "Serverless Scale" (Best ROI)
**Strategies:** 1B (Lambda) + 2 (Chunking) + 5 (Async)
**Effort:** 1-2 weeks
**Speedup:** 10-15x
**New Duration:** 2-4 minutes
**Cost:** <$5/month

### Scenario C: "Enterprise Grade" (Maximum Performance)
**Strategies:** 1B (Lambda) + 2 (Chunking) + 3 (Caching) + 5 (Async)
**Effort:** 3-4 weeks
**Speedup:** First run 10-15x, daily runs 50-100x
**New Duration:** First: 2-4 min, Daily: 1-2 min
**Cost:** $5-10/month (Lambda + Redis)

---

## Recommended Implementation Roadmap

### Phase 1: Quick Wins (Week 1) ⚡
1. ✅ **Optimize modality selection** - DONE in V5
2. ⚡ **Add async concurrency** - 2-3x speedup, easy
3. ⚡ **Implement modality prioritization** - Better UX
4. ⚡ **Add date chunking logic** - Foundation for parallel

**Expected Result:** 15-20 minute runs

### Phase 2: Serverless Parallel (Week 2-3) 🚀
1. Set up AWS Lambda function for worker
2. Implement coordinator/aggregator
3. Deploy multi-worker architecture
4. Test with 4-8 workers

**Expected Result:** 2-4 minute runs

### Phase 3: Intelligent Caching (Week 4+) 💾
1. Design cache schema (PostgreSQL or Redis)
2. Implement incremental fetch logic
3. Add cache invalidation strategy
4. Monitor cache hit rates

**Expected Result:** 1-2 minute daily runs

---

## Technical Considerations

### PNCP API Terms of Service
- ⚠️ **Important:** Verify PNCP allows distributed access
- ✅ Publicly accessible API (no auth required)
- ⚠️ Rate limits exist for a reason (60/min, 1000/hour)
- 🎯 **Recommendation:** Start with 4-8 workers, monitor for blocks

### Rate Limit Math
- **Current:** 1 IP = 60 req/min = 3,600 req/hour
- **With 4 IPs:** 4 × 60 = 240 req/min = 14,400 req/hour
- **With 8 IPs:** 8 × 60 = 480 req/min = 28,800 req/hour
- **Need:** ~200 requests for 5,000 tenders
- **Time:** 200 req ÷ 240 req/min = **<1 minute with 4 IPs**

### Error Handling
- Implement exponential backoff
- Handle 429 (rate limit) responses
- Retry failed chunks independently
- Aggregate partial results

---

## Cost Analysis

| Strategy | Setup Effort | Monthly Cost | Speedup | New Duration |
|----------|--------------|--------------|---------|--------------|
| V5 (Current) | - | $0 | 1x | 34 min |
| Quick Wins | 2-3 days | $0 | 2-3x | 11-17 min |
| AWS Lambda | 1-2 weeks | <$5 | 10-15x | 2-4 min |
| Lambda + Cache | 3-4 weeks | $5-10 | 15-20x (first run), 50x+ (daily) | 2-4 min (first), 1-2 min (daily) |

---

## Success Metrics

### Current (V5 Baseline)
- ⏱️ Duration: 34 minutes (Stage 1)
- 📊 Tenders: 3,940 fetched
- 💊 Medical: 391 found
- 💰 Cost: $0/month

### Target (After Phase 2)
- ⏱️ Duration: <5 minutes (Stage 1)
- 📊 Tenders: 5,000+ fetched
- 💊 Medical: 500+ found
- 💰 Cost: <$5/month
- 🎯 Success Rate: 95%+ of target tenders

### Stretch Goal (After Phase 3)
- ⏱️ Duration: 1-2 minutes (daily incremental)
- 📊 Tenders: All new tenders since last run
- 💊 Medical: Real-time discovery
- 💰 Cost: $5-10/month
- 🎯 Update Frequency: Multiple times per day

---

## Next Steps

1. **Discuss & Prioritize:** Which scenario fits your needs?
2. **Proof of Concept:** Implement Phase 1 (Quick Wins) first
3. **Measure Baseline:** Run tests to confirm improvements
4. **Scale Gradually:** Add workers incrementally (2 → 4 → 8)
5. **Monitor & Optimize:** Track API response times, errors, costs

---

## Questions to Explore Together

1. **Budget:** What monthly cost is acceptable? ($0, $5, $10, $50?)
2. **Urgency:** Need results in minutes or hours acceptable?
3. **Frequency:** Run once/day, multiple times/day, or continuous?
4. **Infrastructure:** Preference for AWS, GCP, Azure, or other?
5. **Maintenance:** Self-managed or fully serverless?
6. **Compliance:** Any restrictions on distributed/parallel access?

---

**Created:** 2025-10-01
**Version:** V5 Baseline Analysis
**Author:** Optimization Analysis based on test_runs/run_20251001_173957/
