# Safe Multi-IP Parallelization Strategy

**Created:** 2025-10-01
**Purpose:** Avoid API blocking when implementing multi-IP parallel fetching

## Current Situation

### What We Know
- **Current rate limit observed:** 60 req/min, 1000 req/hour per IP
- **PNCP API:** Public consultation API, no authentication required
- **Current usage:** ~6 API calls/minute (10% of limit)
- **API response:** Returns 429 status code when rate limited
- **Existing protection:** RateLimiter class with exponential backoff

### What We DON'T Know
- Official PNCP terms of service for consultation API
- Whether distributed access from multiple IPs is explicitly prohibited
- If there are server-side protections against coordinated requests
- Whether there's an IP ban mechanism for abuse

## Risk Assessment

### 🔴 High Risk Behaviors (AVOID)
1. **Aggressive parallel scaling**
   - Starting with 10+ workers immediately
   - Exceeding 4x current per-IP rate limit

2. **Obvious bot signatures**
   - All requests from same cloud provider subnet
   - Identical User-Agent strings
   - Perfectly synchronized request patterns

3. **Ignoring 429 responses**
   - Not implementing exponential backoff
   - Retrying immediately after rate limit

4. **No monitoring/alerting**
   - Can't detect if being blocked
   - Can't stop quickly if issues arise

### 🟡 Medium Risk Behaviors (USE WITH CAUTION)
1. **Conservative parallel scaling**
   - 2-4 workers initially
   - Gradual ramp-up over days/weeks

2. **Cloud-based IPs**
   - GCP, AWS, Azure IPs are easy to identify
   - But legitimate businesses use them

3. **Consistent traffic patterns**
   - Same queries every day
   - But acceptable if within limits

### 🟢 Low Risk Behaviors (SAFE)
1. **Respecting rate limits**
   - Stay under 60/min per IP
   - Never exceed 1000/hour per IP

2. **Proper error handling**
   - Back off on 429 responses
   - Exponential retry delays

3. **Transparent identification**
   - Descriptive User-Agent
   - Contact information in headers

4. **Legitimate use case**
   - Public procurement monitoring
   - Medical supply tracking
   - Healthcare optimization

## Recommended Safe Implementation Strategy

### Phase 1: Gradual Ramp-Up (Week 1-2)

**Start with 2 workers** instead of 8-10

```python
# Conservative multi-worker configuration
WORKER_CONFIG = {
    'num_workers': 2,  # Start small
    'requests_per_minute_per_worker': 40,  # Under 60/min limit
    'max_retries': 3,
    'exponential_backoff_base': 2,  # 2s, 4s, 8s
    'circuit_breaker_threshold': 5  # Stop after 5 consecutive failures
}
```

**Benefits:**
- 2x speedup (34 min → 17 min)
- Low risk profile
- Easy to monitor
- Can increase later if no issues

### Phase 2: Monitoring & Validation (Week 2-3)

**Implement comprehensive monitoring before scaling:**

```python
class MultiWorkerMonitor:
    def __init__(self):
        self.metrics = {
            'total_requests': 0,
            'successful_requests': 0,
            'rate_limited_429': 0,
            'server_errors_5xx': 0,
            'timeouts': 0,
            'blocks_detected': 0,
            'workers_active': 0
        }
        self.alert_thresholds = {
            'rate_limit_ratio': 0.05,  # Alert if >5% requests rate-limited
            'error_ratio': 0.10,  # Alert if >10% errors
            'consecutive_failures': 5  # Alert if 5 failures in a row
        }

    async def check_health(self):
        """Detect if we're being blocked or having issues"""
        if self.metrics['rate_limited_429'] / max(self.metrics['total_requests'], 1) > 0.10:
            logger.critical("⚠️  HIGH RATE LIMIT RATE - Reduce workers or slow down!")
            return False

        if self.metrics['server_errors_5xx'] > 10:
            logger.warning("Multiple server errors - PNCP may be unstable")
            return False

        return True
```

**Monitor for these warning signs:**
- ❌ **Sudden increase in 429 responses** (>5% of requests)
- ❌ **403 Forbidden responses** (possible IP ban)
- ❌ **Connection timeouts** (possible rate limiting)
- ❌ **Consistent 5xx errors** (server overload)

### Phase 3: Scale If Safe (Week 3-4)

**Only scale to 4 workers if:**
✅ 2 workers running smoothly for 1+ week
✅ <1% rate limit responses
✅ No 403 or blocking detected
✅ PNCP hasn't contacted you

```python
# After validation, scale conservatively
VALIDATED_WORKER_CONFIG = {
    'num_workers': 4,  # Double from 2 to 4
    'requests_per_minute_per_worker': 45,  # Still under limit
    'ramp_up_delay': 300  # 5 min between starting each worker
}
```

## Safe Architecture Design

### 1. Transparent Identification

```python
# Be transparent about who you are
HEADERS = {
    'User-Agent': 'MedicalProcurementMonitor/1.0 (Healthcare Supply Tracking; contact@yourdomain.com)',
    'X-Purpose': 'Public procurement monitoring for medical supplies',
    'X-Contact': 'your-email@domain.com'
}
```

### 2. Distributed Workers with Jitter

```python
async def start_worker_with_jitter(worker_id, delay_seconds):
    """Start workers with random delays to avoid synchronized patterns"""
    jitter = random.uniform(0, delay_seconds)
    await asyncio.sleep(jitter)

    logger.info(f"Starting worker {worker_id} after {jitter:.1f}s jitter")
    # ... start worker
```

### 3. Circuit Breaker Pattern

```python
class CircuitBreaker:
    def __init__(self, threshold=5, timeout=300):
        self.failure_count = 0
        self.threshold = threshold
        self.timeout = timeout  # Seconds before retry
        self.last_failure_time = None
        self.state = 'CLOSED'  # CLOSED = working, OPEN = stopped

    async def call(self, func, *args, **kwargs):
        if self.state == 'OPEN':
            # Check if timeout expired
            if time.time() - self.last_failure_time > self.timeout:
                self.state = 'HALF_OPEN'  # Try again
            else:
                raise Exception(f"Circuit breaker OPEN - waiting {self.timeout}s")

        try:
            result = await func(*args, **kwargs)
            self.failure_count = 0  # Reset on success
            self.state = 'CLOSED'
            return result
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()

            if self.failure_count >= self.threshold:
                self.state = 'OPEN'
                logger.critical(f"Circuit breaker OPEN after {self.failure_count} failures")

            raise
```

### 4. Respectful Rate Limiting

```python
class RespectfulRateLimiter(RateLimiter):
    """Enhanced rate limiter with safety margins"""

    def __init__(self):
        # Use 75% of known limits as safety margin
        super().__init__(
            max_requests_per_minute=45,  # 75% of 60
            max_requests_per_hour=750    # 75% of 1000
        )
        self.backoff_multiplier = 1.0  # Increase if rate-limited

    async def handle_rate_limit_response(self):
        """If we get 429, be MORE conservative"""
        self.backoff_multiplier *= 1.5
        logger.warning(f"Rate limited - reducing speed by {self.backoff_multiplier}x")

        # Temporarily reduce our limit
        self.max_per_minute = int(45 / self.backoff_multiplier)
```

## Alternative: Conservative Async Concurrency (RECOMMENDED FIRST)

**Instead of multi-IP**, try async concurrency within single IP first:

```python
# No infrastructure needed, $0 cost, low risk
async def concurrent_fetch_safe(pages, max_concurrent=5):
    """Fetch multiple pages concurrently within rate limit"""
    semaphore = asyncio.Semaphore(max_concurrent)

    async def fetch_with_limit(page):
        async with semaphore:
            await asyncio.sleep(1.2)  # Ensure <60/min (60s/60 = 1s min)
            return await fetch_page(page)

    results = await asyncio.gather(*[fetch_with_limit(p) for p in pages])
    return results
```

**Benefits:**
- 3-5x speedup (34 min → 7-11 min)
- Zero infrastructure cost
- No IP blocking risk
- Easy to implement
- Stays within single-IP limits

## Red Flags to Watch For

### Immediate Action Required If You See:

1. **403 Forbidden responses**
   - Stop all workers immediately
   - Wait 24 hours
   - Review logs for cause
   - Contact PNCP support

2. **Connection refused/timeouts**
   - Reduce worker count by 50%
   - Increase delays between requests
   - Monitor for 24 hours

3. **Consistent 429 even at low rates**
   - May indicate per-user (not per-IP) limiting
   - Fall back to single IP
   - Contact PNCP support

4. **Email/contact from PNCP**
   - Stop ALL automated access immediately
   - Respond professionally
   - Explain legitimate use case
   - Request guidance on acceptable usage

## Recommended Rollout Plan

### Week 1: Baseline (Current System)
- Continue with single IP
- Implement monitoring infrastructure
- Log all response codes and timing
- Establish baseline metrics

### Week 2: Enhanced Single-IP (Async Concurrency)
- Implement concurrent requests within single IP
- Start with 3 concurrent (20/min effective)
- Monitor for issues
- If stable, increase to 5 concurrent (30/min)
- **Expected: 34 min → 10-15 min**

### Week 3: Evaluation Point
**If async concurrency works well:**
- May not need multi-IP at all!
- 10-15 minutes is acceptable for most use cases

**If still too slow:**
- Proceed to Phase 1 (2 workers)
- Monitor heavily
- Ramp up gradually

### Week 4+: Careful Scaling
- Only if Week 3 shows zero issues
- Add 1 worker at a time
- Wait 1 week between increases
- Never exceed 4-6 workers total

## Legal & Ethical Considerations

### ✅ In Your Favor:
- PNCP is public data portal
- No authentication required
- Consultation API is designed for external access
- Legitimate use case (healthcare supply monitoring)
- Staying within technical rate limits

### ⚠️ Considerations:
- No explicit "multi-IP allowed" documentation found
- Government APIs may have undocumented policies
- Better to ask forgiveness than permission? NO - better to be conservative

### 📞 Recommended: Contact PNCP First

Before implementing multi-IP, consider contacting PNCP:

**Email/Phone:** Support channels at gov.br/pncp
**Message template:**
```
Subject: API Usage Question - Automated Procurement Monitoring

Hello PNCP Team,

We are developing a system to monitor medical supply procurements
across Brazilian states to optimize healthcare purchasing decisions.

We use the PNCP Consultation API to fetch tender data programmatically.
Currently we make ~6 requests/minute from a single IP, well within
the 60/min limit we've observed.

To process multiple states efficiently, we're considering distributing
requests across 2-4 cloud instances. Each would still respect the
60 req/min limit.

Questions:
1. Is this acceptable under PNCP's usage policies?
2. Are there any restrictions on distributed/parallel access?
3. Should we follow any specific guidelines?

We want to ensure our usage is compliant and respectful of PNCP resources.

Thank you,
[Your contact information]
```

## Summary Recommendation

### 🎯 **Start with Async Concurrency (NOT Multi-IP)**

**Reasons:**
1. **Lower risk:** No IP blocking concerns
2. **$0 cost:** No infrastructure needed
3. **Good speedup:** 3-5x faster (34min → 7-11min)
4. **Easy to implement:** Change 10 lines of code
5. **Reversible:** Can disable instantly if issues

**Only proceed to multi-IP if:**
- Async concurrency implemented successfully
- Still too slow after 2 weeks
- No issues with PNCP responses
- Ideally after contacting PNCP support

### Implementation Priority:

1. ✅ **Week 1:** Add monitoring/logging
2. ✅ **Week 2:** Implement async concurrency (Strategy 5 from OPTIMIZATION_PLAN.md)
3. ⏸️  **Week 3:** Evaluate - do we still need multi-IP?
4. ⚠️  **Week 4+:** If needed, start with 2 workers + heavy monitoring

This conservative approach protects your access while still achieving significant speedups.
