-- Database Migration: Add CATMAT Tracking and Performance Optimization
-- Purpose: Add CATMAT code tracking, sampling flags, and materialized views
-- Author: Optimized Discovery System
-- Date: 2025-01-XX

-- ============================================================================
-- PHASE 1: Add CATMAT Tracking Columns to tender_items
-- ============================================================================

-- Add CATMAT tracking columns
ALTER TABLE tender_items
ADD COLUMN IF NOT EXISTS catmat_codes TEXT[] DEFAULT '{}',
ADD COLUMN IF NOT EXISTS has_medical_catmat BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS catmat_score_boost INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS sample_analyzed BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS medical_confidence_score FLOAT DEFAULT 0.0;

-- Add comments for documentation
COMMENT ON COLUMN tender_items.catmat_codes IS 'Array of CATMAT classification codes extracted from item description';
COMMENT ON COLUMN tender_items.has_medical_catmat IS 'True if item has medical CATMAT codes (Group 65XX)';
COMMENT ON COLUMN tender_items.catmat_score_boost IS 'Score boost applied due to CATMAT code presence';
COMMENT ON COLUMN tender_items.sample_analyzed IS 'True if item was analyzed in Stage 3 sampling';
COMMENT ON COLUMN tender_items.medical_confidence_score IS 'Confidence score for medical classification (0-100)';

-- ============================================================================
-- PHASE 2: Create Indexes for Performance
-- ============================================================================

-- Index for medical CATMAT lookups (partial index for efficiency)
CREATE INDEX IF NOT EXISTS idx_tender_items_medical_catmat
ON tender_items(has_medical_catmat)
WHERE has_medical_catmat = TRUE;

-- Index for CATMAT code searches (GIN index for array containment)
CREATE INDEX IF NOT EXISTS idx_tender_items_catmat_codes
ON tender_items USING GIN(catmat_codes);

-- Index for sampled items
CREATE INDEX IF NOT EXISTS idx_tender_items_sample_analyzed
ON tender_items(sample_analyzed)
WHERE sample_analyzed = TRUE;

-- Composite index for medical items with high confidence
CREATE INDEX IF NOT EXISTS idx_tender_items_medical_confidence
ON tender_items(has_medical_catmat, medical_confidence_score)
WHERE has_medical_catmat = TRUE AND medical_confidence_score >= 70.0;

-- ============================================================================
-- PHASE 3: Create Materialized View for Known Medical Organizations
-- ============================================================================

-- Drop existing view if exists
DROP MATERIALIZED VIEW IF EXISTS known_medical_orgs CASCADE;

-- Create materialized view with refresh capability
CREATE MATERIALIZED VIEW known_medical_orgs AS
SELECT DISTINCT
    o.id,
    o.cnpj,
    o.name,
    o.state_code,
    o.organization_type,
    o.government_level,
    COUNT(DISTINCT t.id) as tender_count,
    MAX(t.created_at) as last_tender_date,
    SUM(t.total_homologated_value) as total_spending,
    AVG(t.total_homologated_value) as avg_tender_value,
    -- Medical relevance metrics
    COUNT(DISTINCT CASE WHEN ti.has_medical_catmat THEN t.id END) as medical_tender_count,
    (COUNT(DISTINCT CASE WHEN ti.has_medical_catmat THEN t.id END)::float /
     NULLIF(COUNT(DISTINCT t.id), 0) * 100) as medical_percentage
FROM organizations o
JOIN tenders t ON o.id = t.organization_id
LEFT JOIN tender_items ti ON t.id = ti.tender_id
WHERE o.organization_type IN ('hospital', 'health_secretariat', 'clinic')
   OR o.name ILIKE '%hospital%'
   OR o.name ILIKE '%saúde%'
   OR o.name ILIKE '%saude%'
   OR o.name ILIKE '%clínica%'
   OR o.name ILIKE '%clinica%'
GROUP BY o.id, o.cnpj, o.name, o.state_code, o.organization_type, o.government_level
HAVING COUNT(DISTINCT t.id) >= 2  -- At least 2 tenders
   OR COUNT(DISTINCT CASE WHEN ti.has_medical_catmat THEN t.id END) >= 1;  -- Or 1+ medical tender

-- Create unique index for faster refresh
CREATE UNIQUE INDEX idx_known_medical_orgs_id ON known_medical_orgs(id);

-- Create additional indexes
CREATE INDEX idx_known_medical_orgs_state ON known_medical_orgs(state_code);
CREATE INDEX idx_known_medical_orgs_cnpj ON known_medical_orgs(cnpj);
CREATE INDEX idx_known_medical_orgs_medical_pct ON known_medical_orgs(medical_percentage) WHERE medical_percentage >= 50;

-- Add comments
COMMENT ON MATERIALIZED VIEW known_medical_orgs IS 'Cached list of known medical organizations for fast filtering';

-- ============================================================================
-- PHASE 4: Create Materialized View for Medical Items Summary
-- ============================================================================

-- Drop existing view if exists
DROP MATERIALIZED VIEW IF EXISTS medical_items_summary CASCADE;

-- Create comprehensive medical items view
CREATE MATERIALIZED VIEW medical_items_summary AS
SELECT
    ti.id as item_id,
    ti.tender_id,
    t.control_number,
    t.state_code,
    t.publication_date,
    o.id as organization_id,
    o.name as organization_name,
    o.cnpj as organization_cnpj,
    o.organization_type,
    ti.item_number,
    ti.description,
    ti.catmat_codes,
    ti.has_medical_catmat,
    ti.medical_confidence_score,
    ti.unit,
    ti.quantity,
    ti.homologated_unit_value,
    ti.homologated_total_value,
    ti.estimated_unit_value,
    ti.estimated_total_value,
    ti.winner_name,
    ti.winner_cnpj,
    -- Calculated fields
    (ti.homologated_total_value - ti.estimated_total_value) as value_difference,
    CASE
        WHEN ti.estimated_total_value > 0 THEN
            ((ti.homologated_total_value - ti.estimated_total_value) / ti.estimated_total_value * 100)
        ELSE NULL
    END as price_variance_percent
FROM tender_items ti
JOIN tenders t ON ti.tender_id = t.id
JOIN organizations o ON t.organization_id = o.id
WHERE ti.has_medical_catmat = TRUE
   OR ti.description ILIKE '%curativo%'
   OR ti.description ILIKE '%cateter%'
   OR ti.description ILIKE '%seringa%'
   OR ti.description ILIKE '%equipamento médico%'
   OR ti.description ILIKE '%material hospitalar%';

-- Create indexes on materialized view
CREATE INDEX idx_medical_items_summary_tender ON medical_items_summary(tender_id);
CREATE INDEX idx_medical_items_summary_org ON medical_items_summary(organization_id);
CREATE INDEX idx_medical_items_summary_state ON medical_items_summary(state_code);
CREATE INDEX idx_medical_items_summary_date ON medical_items_summary(publication_date);
CREATE INDEX idx_medical_items_summary_catmat ON medical_items_summary USING GIN(catmat_codes);
CREATE INDEX idx_medical_items_summary_value ON medical_items_summary(homologated_total_value) WHERE homologated_total_value IS NOT NULL;

-- Add comments
COMMENT ON MATERIALIZED VIEW medical_items_summary IS 'Pre-joined medical items with organization and tender data for fast analytics';

-- ============================================================================
-- PHASE 5: Create Refresh Functions
-- ============================================================================

-- Function to refresh all materialized views
CREATE OR REPLACE FUNCTION refresh_medical_views()
RETURNS void AS $$
BEGIN
    -- Refresh known medical orgs (can be concurrent after first refresh)
    REFRESH MATERIALIZED VIEW CONCURRENTLY known_medical_orgs;

    -- Refresh medical items summary
    REFRESH MATERIALIZED VIEW medical_items_summary;

    -- Log refresh
    RAISE NOTICE 'Materialized views refreshed at %', NOW();
END;
$$ LANGUAGE plpgsql;

-- Add comment
COMMENT ON FUNCTION refresh_medical_views() IS 'Refresh all medical-related materialized views';

-- ============================================================================
-- PHASE 6: Add Statistics and Optimization
-- ============================================================================

-- Update statistics for new columns
ANALYZE tender_items;

-- Update statistics for organizations
ANALYZE organizations;
ANALYZE tenders;

-- ============================================================================
-- PHASE 7: Create Helper Views for Analytics
-- ============================================================================

-- View: Top CATMAT codes by frequency
CREATE OR REPLACE VIEW top_catmat_codes AS
SELECT
    unnest(catmat_codes) as catmat_code,
    COUNT(*) as frequency,
    COUNT(DISTINCT tender_id) as tender_count,
    AVG(homologated_unit_value) as avg_unit_price,
    SUM(quantity) as total_quantity
FROM tender_items
WHERE has_medical_catmat = TRUE
GROUP BY catmat_code
ORDER BY frequency DESC;

COMMENT ON VIEW top_catmat_codes IS 'Top CATMAT codes ranked by frequency';

-- View: Medical procurement by state
CREATE OR REPLACE VIEW medical_procurement_by_state AS
SELECT
    t.state_code,
    COUNT(DISTINCT t.id) as tender_count,
    COUNT(DISTINCT o.id) as org_count,
    SUM(t.total_homologated_value) as total_value,
    AVG(t.total_homologated_value) as avg_tender_value,
    COUNT(DISTINCT ti.catmat_codes) as unique_catmat_codes
FROM tenders t
JOIN organizations o ON t.organization_id = o.id
LEFT JOIN tender_items ti ON t.id = ti.tender_id
WHERE ti.has_medical_catmat = TRUE
GROUP BY t.state_code
ORDER BY total_value DESC;

COMMENT ON VIEW medical_procurement_by_state IS 'Medical procurement statistics by state';

-- ============================================================================
-- PHASE 8: Create Performance Monitoring Table
-- ============================================================================

-- Table for tracking discovery performance
CREATE TABLE IF NOT EXISTS discovery_performance (
    id SERIAL PRIMARY KEY,
    run_date TIMESTAMP DEFAULT NOW(),
    state_code VARCHAR(2),
    stage_name VARCHAR(50),
    tenders_in INTEGER DEFAULT 0,
    tenders_out INTEGER DEFAULT 0,
    api_calls INTEGER DEFAULT 0,
    duration_seconds FLOAT DEFAULT 0,
    cache_hits INTEGER DEFAULT 0,
    cache_misses INTEGER DEFAULT 0,
    errors INTEGER DEFAULT 0,
    notes TEXT
);

-- Index for performance queries
CREATE INDEX idx_discovery_performance_date ON discovery_performance(run_date DESC);
CREATE INDEX idx_discovery_performance_state ON discovery_performance(state_code);
CREATE INDEX idx_discovery_performance_stage ON discovery_performance(stage_name);

COMMENT ON TABLE discovery_performance IS 'Performance metrics for multi-stage discovery operations';

-- ============================================================================
-- PHASE 9: Grant Permissions (adjust as needed)
-- ============================================================================

-- Grant read access to views (adjust username as needed)
-- GRANT SELECT ON known_medical_orgs TO your_application_user;
-- GRANT SELECT ON medical_items_summary TO your_application_user;
-- GRANT SELECT ON top_catmat_codes TO your_application_user;
-- GRANT SELECT ON medical_procurement_by_state TO your_application_user;

-- ============================================================================
-- PHASE 10: Initial Data Population (if needed)
-- ============================================================================

-- Update existing records with CATMAT codes (example - adjust logic as needed)
-- This is a sample - should be run through your Python classifier
/*
UPDATE tender_items SET
    has_medical_catmat = (description ~ '6[5][0-9]{2,6}'),
    medical_confidence_score = CASE
        WHEN description ~ '6[5][0-9]{2,6}' THEN 95.0
        ELSE 0.0
    END
WHERE catmat_codes = '{}' AND description IS NOT NULL;
*/

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- Verify new columns exist
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'tender_items'
AND column_name IN ('catmat_codes', 'has_medical_catmat', 'catmat_score_boost', 'sample_analyzed', 'medical_confidence_score');

-- Verify indexes exist
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'tender_items'
AND indexname LIKE '%catmat%';

-- Verify materialized views exist
SELECT matviewname, definition
FROM pg_matviews
WHERE matviewname IN ('known_medical_orgs', 'medical_items_summary');

-- Check materialized view row counts
SELECT 'known_medical_orgs' as view_name, COUNT(*) as row_count FROM known_medical_orgs
UNION ALL
SELECT 'medical_items_summary', COUNT(*) FROM medical_items_summary;

-- ============================================================================
-- ROLLBACK SCRIPT (use if migration needs to be reverted)
-- ============================================================================
/*
-- Drop materialized views
DROP MATERIALIZED VIEW IF EXISTS medical_items_summary CASCADE;
DROP MATERIALIZED VIEW IF EXISTS known_medical_orgs CASCADE;

-- Drop views
DROP VIEW IF EXISTS top_catmat_codes;
DROP VIEW IF EXISTS medical_procurement_by_state;

-- Drop function
DROP FUNCTION IF EXISTS refresh_medical_views();

-- Drop performance table
DROP TABLE IF EXISTS discovery_performance;

-- Remove columns from tender_items
ALTER TABLE tender_items
DROP COLUMN IF EXISTS catmat_codes,
DROP COLUMN IF EXISTS has_medical_catmat,
DROP COLUMN IF EXISTS catmat_score_boost,
DROP COLUMN IF EXISTS sample_analyzed,
DROP COLUMN IF EXISTS medical_confidence_score;
*/

-- ============================================================================
-- MIGRATION COMPLETE
-- ============================================================================

-- Log completion
DO $$
BEGIN
    RAISE NOTICE '================================================';
    RAISE NOTICE 'Database migration completed successfully!';
    RAISE NOTICE 'Timestamp: %', NOW();
    RAISE NOTICE '================================================';
END $$;
