# AI Matching Database Architecture

Best practices for organizing AI matching data in PostgreSQL.

---

## Architecture Decision

**Use single database with dedicated tables for matching workflow.**

### Why Not Separate Database?

❌ **Separate Database Issues:**
- Data duplication and sync complexity
- Can't use JOINs across databases easily
- More infrastructure to manage
- Overkill for ~9,000 items

✅ **Single Database Benefits:**
- Transactional integrity
- Easy JOINs with source data
- Simpler infrastructure
- ACID guarantees for results

---

## Recommended Schema

### Option A: Minimal (Quick to implement)

```sql
-- Use existing tables + add tracking fields

-- Existing tables
tender_items (existing)
fernandes_products (existing)
matched_products (existing)

-- Add processing status to tender_items
ALTER TABLE tender_items ADD COLUMN IF NOT EXISTS
  matching_status VARCHAR(20) DEFAULT 'pending';
  -- Values: 'pending', 'queued', 'processing', 'matched', 'rejected'

ALTER TABLE tender_items ADD COLUMN IF NOT EXISTS
  matching_queued_at TIMESTAMP;

-- Add session tracking to matched_products
ALTER TABLE matched_products ADD COLUMN IF NOT EXISTS
  matching_session_id UUID;
```

**Pros:** Minimal changes, works immediately
**Cons:** Mixes concerns in existing tables

---

### Option B: Dedicated Tables (Recommended)

```sql
-- 1. MATCHING QUEUE: Filtered items ready for AI matching
CREATE TABLE IF NOT EXISTS matching_queue (
    id SERIAL PRIMARY KEY,
    tender_item_id INTEGER REFERENCES tender_items(id) UNIQUE,

    -- Metadata from filtering
    filter_keywords TEXT[],  -- ['curativo', 'transparente']
    priority INTEGER DEFAULT 0,  -- High-value items first

    -- Processing status
    status VARCHAR(20) DEFAULT 'pending',
    -- 'pending', 'processing', 'matched', 'rejected', 'error'

    -- AI matching attempts
    attempts INTEGER DEFAULT 0,
    last_attempt_at TIMESTAMP,
    error_message TEXT,

    -- Timestamps
    queued_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP,

    -- Indexing
    CONSTRAINT valid_status CHECK (status IN ('pending', 'processing', 'matched', 'rejected', 'error'))
);

CREATE INDEX idx_matching_queue_status ON matching_queue(status);
CREATE INDEX idx_matching_queue_priority ON matching_queue(priority DESC, queued_at);


-- 2. MATCHING SESSIONS: Track matching runs (audit trail)
CREATE TABLE IF NOT EXISTS matching_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Session info
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    status VARCHAR(20) DEFAULT 'running',
    -- 'running', 'completed', 'failed', 'cancelled'

    -- Configuration
    filter_keywords TEXT[],
    confidence_threshold INTEGER DEFAULT 70,
    batch_size INTEGER DEFAULT 50,

    -- Statistics
    total_items INTEGER,
    processed_items INTEGER DEFAULT 0,
    matched_items INTEGER DEFAULT 0,
    rejected_items INTEGER DEFAULT 0,
    error_items INTEGER DEFAULT 0,

    -- Cost tracking
    api_calls INTEGER DEFAULT 0,
    estimated_cost DECIMAL(10, 4),

    -- Metadata
    initiated_by VARCHAR(100),  -- 'manual', 'cron', 'api'
    notes TEXT
);

CREATE INDEX idx_matching_sessions_status ON matching_sessions(status);
CREATE INDEX idx_matching_sessions_started ON matching_sessions(started_at DESC);


-- 3. MATCHED PRODUCTS: Update existing table
ALTER TABLE matched_products ADD COLUMN IF NOT EXISTS
  matching_session_id UUID REFERENCES matching_sessions(id);

ALTER TABLE matched_products ADD COLUMN IF NOT EXISTS
  batch_number INTEGER;  -- Which batch in the session


-- 4. MANUAL REVIEWS: For medium-confidence matches
CREATE TABLE IF NOT EXISTS matching_manual_reviews (
    id SERIAL PRIMARY KEY,
    tender_item_id INTEGER REFERENCES tender_items(id),
    fernandes_product_id INTEGER REFERENCES fernandes_products(id),

    -- AI suggestion
    ai_confidence INTEGER,
    ai_reasoning TEXT,

    -- Review status
    review_status VARCHAR(20) DEFAULT 'pending',
    -- 'pending', 'approved', 'rejected', 'needs_info'

    reviewed_by VARCHAR(100),
    reviewed_at TIMESTAMP,
    review_notes TEXT,

    -- If approved, link to matched_products
    matched_product_id INTEGER REFERENCES matched_products(id),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_manual_reviews_status ON matching_manual_reviews(review_status);
CREATE INDEX idx_manual_reviews_confidence ON matching_manual_reviews(ai_confidence DESC);
```

---

## Data Flow

### Phase 1: Filter & Queue
```sql
-- Step 1: Extract filtered items and add to queue
INSERT INTO matching_queue (tender_item_id, filter_keywords, priority)
SELECT
    ti.id,
    ARRAY['curativo', 'transparente'],
    CASE
        WHEN ti.homologated_unit_value > 100 THEN 3  -- High priority
        WHEN ti.homologated_unit_value > 10 THEN 2   -- Medium priority
        ELSE 1                                        -- Low priority
    END
FROM tender_items ti
WHERE (
    LOWER(ti.description) LIKE '%curativo%'
    OR LOWER(ti.description) LIKE '%transparente%'
)
AND ti.id NOT IN (
    SELECT tender_item_id FROM matching_queue
)
AND ti.homologated_unit_value > 0;
```

### Phase 2: Create Session
```sql
-- Create matching session
INSERT INTO matching_sessions (
    filter_keywords,
    total_items,
    batch_size,
    initiated_by
)
SELECT
    ARRAY['curativo', 'transparente'],
    COUNT(*),
    50,
    'manual'
FROM matching_queue
WHERE status = 'pending'
RETURNING id;  -- Use this session_id for all matches
```

### Phase 3: Process Batches
```sql
-- Get next batch to process (ordered by priority)
SELECT
    mq.id as queue_id,
    ti.id,
    ti.description,
    ti.quantity,
    ti.unit,
    ti.homologated_unit_value
FROM matching_queue mq
JOIN tender_items ti ON mq.tender_item_id = ti.id
WHERE mq.status = 'pending'
ORDER BY mq.priority DESC, mq.queued_at
LIMIT 50
FOR UPDATE SKIP LOCKED;  -- Concurrent processing support

-- Mark as processing
UPDATE matching_queue
SET
    status = 'processing',
    attempts = attempts + 1,
    last_attempt_at = CURRENT_TIMESTAMP
WHERE id IN (batch_ids);
```

### Phase 4: Save Results
```sql
-- High confidence (≥90%) → matched_products
INSERT INTO matched_products (
    tender_item_id,
    fernandes_product_id,
    match_confidence,
    match_method,
    match_reasoning,
    price_difference_percent,
    matching_session_id,
    batch_number
)
VALUES (...);

-- Update queue status
UPDATE matching_queue
SET
    status = 'matched',
    processed_at = CURRENT_TIMESTAMP
WHERE tender_item_id = ?;

-- Medium confidence (70-89%) → manual_reviews
INSERT INTO matching_manual_reviews (
    tender_item_id,
    fernandes_product_id,
    ai_confidence,
    ai_reasoning
)
VALUES (...);

UPDATE matching_queue
SET status = 'pending'  -- Keep in queue for review
WHERE tender_item_id = ?;
```

### Phase 5: Complete Session
```sql
-- Update session statistics
UPDATE matching_sessions
SET
    completed_at = CURRENT_TIMESTAMP,
    status = 'completed',
    processed_items = (SELECT COUNT(*) FROM matching_queue WHERE matching_session_id = ?),
    matched_items = (SELECT COUNT(*) FROM matched_products WHERE matching_session_id = ?),
    rejected_items = (SELECT COUNT(*) FROM matching_queue WHERE status = 'rejected'),
    api_calls = total_batches,
    estimated_cost = total_batches * 0.001
WHERE id = ?;
```

---

## Querying Patterns

### Get Items Ready for Matching
```sql
-- Get next batch (respects priority)
SELECT
    ti.*,
    mq.priority,
    mq.filter_keywords
FROM matching_queue mq
JOIN tender_items ti ON mq.tender_item_id = ti.id
WHERE mq.status = 'pending'
ORDER BY mq.priority DESC, mq.queued_at
LIMIT 50;
```

### Get Matching Progress
```sql
-- Session progress
SELECT
    id,
    started_at,
    (processed_items::FLOAT / total_items * 100) as progress_pct,
    matched_items,
    rejected_items,
    estimated_cost
FROM matching_sessions
WHERE status = 'running'
ORDER BY started_at DESC;
```

### Get Review Queue
```sql
-- Medium-confidence matches needing review
SELECT
    mr.id,
    ti.description as tender_description,
    fp.name as suggested_product,
    mr.ai_confidence,
    mr.ai_reasoning,
    ti.homologated_unit_value as tender_price,
    fp.price as fernandes_price
FROM matching_manual_reviews mr
JOIN tender_items ti ON mr.tender_item_id = ti.id
JOIN fernandes_products fp ON mr.fernandes_product_id = fp.id
WHERE mr.review_status = 'pending'
ORDER BY mr.ai_confidence DESC;
```

### Get Matching Results
```sql
-- All matches from a session
SELECT
    ti.description,
    fp.name as matched_product,
    mp.match_confidence,
    mp.price_difference_percent,
    ti.homologated_unit_value as tender_price,
    fp.price as fernandes_price
FROM matched_products mp
JOIN tender_items ti ON mp.tender_item_id = ti.id
JOIN fernandes_products fp ON mp.fernandes_product_id = fp.id
WHERE mp.matching_session_id = ?
ORDER BY mp.match_confidence DESC;
```

---

## Gemini Integration

### Read from Database (Recommended)
```python
# In step2_gemini.py

async def load_items_from_database(self, batch_size=50):
    """Load items directly from matching_queue"""

    query = """
        SELECT
            mq.id as queue_id,
            ti.id,
            ti.description,
            ti.quantity,
            ti.unit,
            ti.homologated_unit_value
        FROM matching_queue mq
        JOIN tender_items ti ON mq.tender_item_id = ti.id
        WHERE mq.status = 'pending'
        ORDER BY mq.priority DESC, mq.queued_at
        LIMIT $1
        FOR UPDATE SKIP LOCKED
    """

    items = await conn.fetch(query, batch_size)

    # Mark as processing
    queue_ids = [item['queue_id'] for item in items]
    await conn.execute("""
        UPDATE matching_queue
        SET status = 'processing',
            attempts = attempts + 1,
            last_attempt_at = CURRENT_TIMESTAMP
        WHERE id = ANY($1)
    """, queue_ids)

    return items

async def save_matches_to_database(self, matches, session_id):
    """Save directly to database"""

    for match in matches:
        if match['confidence'] >= 90:
            # High confidence → matched_products
            await conn.execute("""
                INSERT INTO matched_products (...)
                VALUES (...)
            """)

            await conn.execute("""
                UPDATE matching_queue
                SET status = 'matched',
                    processed_at = CURRENT_TIMESTAMP
                WHERE tender_item_id = $1
            """, match['tender_item_id'])

        elif match['confidence'] >= 70:
            # Medium confidence → manual_reviews
            await conn.execute("""
                INSERT INTO matching_manual_reviews (...)
                VALUES (...)
            """)
```

---

## Migration Steps

### Step 1: Create Tables
```bash
python3 ai_matching/utils/create_matching_tables.py
```

### Step 2: Populate Queue
```bash
python3 ai_matching/step1_extract.py --to-database
```

### Step 3: Run Matching
```bash
python3 ai_matching/step2_gemini.py --from-database
```

---

## Performance Considerations

### Indexes
```sql
-- Critical for performance
CREATE INDEX idx_matching_queue_status ON matching_queue(status);
CREATE INDEX idx_matching_queue_priority ON matching_queue(priority DESC, queued_at);
CREATE INDEX idx_tender_items_description ON tender_items USING gin(to_tsvector('portuguese', description));
```

### Partitioning (Optional for large scale)
```sql
-- If matching_queue grows large
CREATE TABLE matching_queue_2025_q1 PARTITION OF matching_queue
    FOR VALUES FROM ('2025-01-01') TO ('2025-04-01');
```

### Concurrent Processing
```sql
-- Use FOR UPDATE SKIP LOCKED for multiple workers
-- Allows parallel processing without conflicts
```

---

## Comparison: File vs Database

| Aspect | Files (Current) | Database (Recommended) |
|--------|----------------|------------------------|
| **Source of Truth** | Multiple (JSON + DB) | Single (DB) |
| **Resumability** | ❌ Must restart | ✅ Track status |
| **Concurrency** | ❌ File locks | ✅ Row-level locks |
| **Audit Trail** | ❌ None | ✅ Full history |
| **Queries** | ❌ Load entire file | ✅ Efficient SQL |
| **Integration** | ❌ Manual sync | ✅ Native JOINs |
| **Scalability** | ❌ Memory limited | ✅ Paginated |
| **Data Integrity** | ❌ Can diverge | ✅ ACID |

---

## Recommendation

**Use Option B (Dedicated Tables) for production:**

1. ✅ Clean separation of concerns
2. ✅ Full audit trail
3. ✅ Resumable processing
4. ✅ Concurrent-safe
5. ✅ Easy to monitor progress
6. ✅ Scales to millions of items

**Keep files for:**
- Initial prototyping ✅
- Backup/export ✅
- Integration with external tools ✅

---

## Implementation Priority

### Phase 1 (Now - Keep working)
- ✅ Use current file-based approach
- ✅ Get first results
- ✅ Validate AI matching quality

### Phase 2 (After validation)
- 🔄 Migrate to database-based workflow
- 🔄 Add matching_queue table
- 🔄 Add matching_sessions table
- 🔄 Update scripts to read/write DB

### Phase 3 (Production)
- 🔄 Add manual_reviews table
- 🔄 Build review interface
- 🔄 Schedule automated runs
- 🔄 Monitor and optimize

---

## Summary

**Best Practice: Single database, dedicated tables**

```
medical (database)
├── tender_items (~9,000)
├── fernandes_products (catalog)
├── matching_queue (filtered, ready for AI)
├── matched_products (high-confidence results)
├── matching_manual_reviews (medium-confidence)
└── matching_sessions (audit trail)
```

**Benefits:**
- Single source of truth
- Transactional integrity
- Resumable processing
- Full audit trail
- Scales to production

**Next Steps:**
1. Validate AI matching with current file-based approach
2. Once confident, migrate to database workflow
3. Add monitoring and automation
