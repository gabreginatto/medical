-- ============================================================
-- ANALYTICS SCHEMA & MATERIALIZED VIEWS
-- Purpose: Create "Excel-like sheets" for easier Looker Studio analysis
--
-- INSTRUCTIONS:
-- 1. Wait until database updates are complete
-- 2. Run this entire file: psql -d your_database -f analytics_views.sql
-- 3. Refresh views periodically with: REFRESH MATERIALIZED VIEW analytics.view_name;
-- ============================================================

-- Create analytics schema (like a separate workbook section)
CREATE SCHEMA IF NOT EXISTS analytics;

-- ============================================================
-- VIEW 1: CURATIVO ITEMS (Wound Dressings)
-- All wound dressing items with tender and organization details
-- ============================================================
CREATE MATERIALIZED VIEW analytics.curativo_items AS
SELECT
    -- Item details
    ti.id as item_id,
    ti.item_number,
    ti.description,
    ti.unit,
    ti.quantity,
    ti.estimated_unit_value,
    ti.estimated_total_value,
    ti.homologated_unit_value,
    ti.homologated_total_value,

    -- Winner information
    ti.winner_name,
    ti.winner_cnpj,

    -- CATMAT information
    ti.catmat_codes,
    ti.has_medical_catmat,
    ti.catmat_score_boost,
    ti.medical_confidence_score,

    -- Tender details
    t.id as tender_id,
    t.control_number,
    t.year as tender_year,
    t.publication_date,
    t.total_homologated_value as tender_total_value,
    t.modality_code,

    -- Organization details
    o.id as organization_id,
    o.cnpj as organization_cnpj,
    o.name as organization_name,
    o.government_level,
    o.organization_type,
    o.state_code,

    -- Calculated fields
    CASE
        WHEN ti.homologated_unit_value > 0 AND ti.estimated_unit_value > 0
        THEN ROUND(((ti.homologated_unit_value - ti.estimated_unit_value) / ti.estimated_unit_value * 100)::numeric, 2)
        ELSE NULL
    END as price_variance_percent,

    ti.created_at

FROM tender_items ti
JOIN tenders t ON ti.tender_id = t.id
JOIN organizations o ON t.organization_id = o.id
WHERE ti.description ILIKE '%curativ%'
   OR ti.description ILIKE '%band%'
   OR ti.description ILIKE '%gaze%'
   OR ti.description ILIKE '%atadura%';

-- Create indexes for faster Looker Studio queries
CREATE INDEX idx_analytics_curativo_state ON analytics.curativo_items(state_code);
CREATE INDEX idx_analytics_curativo_year ON analytics.curativo_items(tender_year);
CREATE INDEX idx_analytics_curativo_org ON analytics.curativo_items(organization_id);
CREATE INDEX idx_analytics_curativo_price ON analytics.curativo_items(homologated_unit_value);

COMMENT ON MATERIALIZED VIEW analytics.curativo_items IS
'Complete view of wound dressing items with pricing, organizations, and tender details.
Refresh with: REFRESH MATERIALIZED VIEW analytics.curativo_items;';


-- ============================================================
-- VIEW 2: MEDICAL ITEMS SUMMARY
-- All high-confidence medical items with CATMAT codes
-- ============================================================
CREATE MATERIALIZED VIEW analytics.medical_items_summary AS
SELECT
    ti.id as item_id,
    ti.description,
    ti.catmat_codes,
    ti.medical_confidence_score,
    ti.homologated_unit_value,
    ti.homologated_total_value,
    ti.quantity,
    ti.unit,
    ti.winner_name,

    t.publication_date,
    t.control_number,
    t.modality_code,

    o.name as organization_name,
    o.state_code,
    o.government_level,

    -- Categorization
    CASE
        WHEN ti.description ILIKE '%curativ%' OR ti.description ILIKE '%gaze%' THEN 'Curativos'
        WHEN ti.description ILIKE '%cirúrgic%' THEN 'Cirúrgico'
        WHEN ti.description ILIKE '%luva%' THEN 'Luvas'
        WHEN ti.description ILIKE '%máscara%' THEN 'Máscaras'
        WHEN ti.description ILIKE '%seringa%' THEN 'Seringas'
        ELSE 'Outros Médicos'
    END as category

FROM tender_items ti
JOIN tenders t ON ti.tender_id = t.id
JOIN organizations o ON t.organization_id = o.id
WHERE ti.has_medical_catmat = TRUE
   OR ti.medical_confidence_score >= 70.0;

CREATE INDEX idx_analytics_medical_category ON analytics.medical_items_summary(category);
CREATE INDEX idx_analytics_medical_state ON analytics.medical_items_summary(state_code);
CREATE INDEX idx_analytics_medical_confidence ON analytics.medical_items_summary(medical_confidence_score);

COMMENT ON MATERIALIZED VIEW analytics.medical_items_summary IS
'High-confidence medical items categorized by type with CATMAT validation.
Refresh with: REFRESH MATERIALIZED VIEW analytics.medical_items_summary;';


-- ============================================================
-- VIEW 3: PRICE ANALYSIS
-- Compare government prices with Fernandes FOB prices
-- DISABLED: matched_products table has different schema than expected
-- ============================================================
-- CREATE MATERIALIZED VIEW analytics.price_analysis AS
-- SELECT
--     mp.id as match_id,
--     ...
-- (COMMENTED OUT - matched_products table has different schema)
-- Uncomment and adapt when product matching is fully implemented


-- ============================================================
-- VIEW 4: STATE SUMMARY
-- Aggregate statistics by state for dashboard overview
-- ============================================================
CREATE MATERIALIZED VIEW analytics.state_summary AS
SELECT
    o.state_code,
    COUNT(DISTINCT t.id) as total_tenders,
    COUNT(DISTINCT o.id) as total_organizations,
    COUNT(ti.id) as total_items,

    -- Medical items stats
    COUNT(ti.id) FILTER (WHERE ti.has_medical_catmat = TRUE) as medical_items_count,
    COUNT(ti.id) FILTER (WHERE ti.description ILIKE '%curativ%') as curativo_items_count,

    -- Financial stats
    SUM(ti.homologated_total_value) as total_homologated_value_brl,
    AVG(ti.homologated_unit_value) as avg_unit_price_brl,

    -- Date range
    MIN(t.publication_date) as earliest_tender,
    MAX(t.publication_date) as latest_tender,

    -- Last updated
    MAX(ti.created_at) as last_item_update

FROM organizations o
JOIN tenders t ON o.id = t.organization_id
JOIN tender_items ti ON t.id = ti.tender_id
GROUP BY o.state_code;

CREATE INDEX idx_analytics_state_code ON analytics.state_summary(state_code);

COMMENT ON MATERIALIZED VIEW analytics.state_summary IS
'State-level aggregated statistics for executive dashboards.
Refresh with: REFRESH MATERIALIZED VIEW analytics.state_summary;';


-- ============================================================
-- VIEW 5: TOP WINNERS
-- Companies winning the most tenders with competitive analysis
-- ============================================================
CREATE MATERIALIZED VIEW analytics.top_winners AS
SELECT
    ti.winner_cnpj,
    ti.winner_name,
    COUNT(DISTINCT ti.tender_id) as tenders_won,
    COUNT(ti.id) as items_won,
    SUM(ti.homologated_total_value) as total_value_won_brl,
    AVG(ti.homologated_unit_value) as avg_unit_price,

    -- Category breakdown
    COUNT(ti.id) FILTER (WHERE ti.description ILIKE '%curativ%') as curativo_items,
    COUNT(ti.id) FILTER (WHERE ti.has_medical_catmat = TRUE) as medical_items,

    -- Geographic presence
    COUNT(DISTINCT t.state_code) as states_active,
    array_agg(DISTINCT t.state_code ORDER BY t.state_code) as states_list,

    -- Time range
    MIN(t.publication_date) as first_win_date,
    MAX(t.publication_date) as last_win_date

FROM tender_items ti
JOIN tenders t ON ti.tender_id = t.id
WHERE ti.winner_cnpj IS NOT NULL
  AND ti.homologated_total_value > 0
GROUP BY ti.winner_cnpj, ti.winner_name
HAVING COUNT(ti.id) >= 5  -- Only winners with 5+ items
ORDER BY total_value_won_brl DESC;

CREATE INDEX idx_analytics_winners_value ON analytics.top_winners(total_value_won_brl);
CREATE INDEX idx_analytics_winners_count ON analytics.top_winners(items_won);

COMMENT ON MATERIALIZED VIEW analytics.top_winners IS
'Top supplier companies by contract value and item count.
Refresh with: REFRESH MATERIALIZED VIEW analytics.top_winners;';


-- ============================================================
-- VIEW 6: SUPER TENDERS
-- High-value tenders with very few items (2-5 items)
-- ============================================================
CREATE MATERIALIZED VIEW analytics.super_tenders AS
WITH tender_item_counts AS (
    SELECT
        tender_id,
        COUNT(*) as item_count,
        SUM(homologated_total_value) as items_total_value
    FROM tender_items
    WHERE homologated_total_value > 0
    GROUP BY tender_id
)
SELECT
    t.id as tender_id,
    t.control_number,
    t.year as tender_year,
    t.publication_date,
    t.total_homologated_value,

    -- Item statistics
    tic.item_count,
    tic.items_total_value,
    ROUND((t.total_homologated_value / tic.item_count)::numeric, 2) as avg_value_per_item,

    -- Organization details
    o.name as organization_name,
    o.cnpj as organization_cnpj,
    o.state_code,
    o.government_level,
    o.organization_type,

    -- Tender details
    t.modality_code,

    -- Value category
    CASE
        WHEN t.total_homologated_value >= 1000000 THEN 'Mega (>R$1M)'
        WHEN t.total_homologated_value >= 500000 THEN 'Large (R$500K-1M)'
        WHEN t.total_homologated_value >= 100000 THEN 'Medium (R$100K-500K)'
        ELSE 'Small (<R$100K)'
    END as value_category,

    -- Efficiency score (higher value / fewer items = higher score)
    ROUND((t.total_homologated_value / tic.item_count)::numeric, 0) as efficiency_score

FROM tenders t
JOIN tender_item_counts tic ON t.id = tic.tender_id
JOIN organizations o ON t.organization_id = o.id
WHERE tic.item_count BETWEEN 2 AND 5  -- Only 2-5 items
  AND t.total_homologated_value >= 15000000  -- At least R$15M
ORDER BY t.total_homologated_value DESC;

CREATE INDEX idx_analytics_super_tenders_value ON analytics.super_tenders(total_homologated_value DESC);
CREATE INDEX idx_analytics_super_tenders_item_count ON analytics.super_tenders(item_count);
CREATE INDEX idx_analytics_super_tenders_state ON analytics.super_tenders(state_code);
CREATE INDEX idx_analytics_super_tenders_efficiency ON analytics.super_tenders(efficiency_score DESC);

COMMENT ON MATERIALIZED VIEW analytics.super_tenders IS
'High-value tenders with minimal items (2-5 items). These "super tenders" often represent
specialized/expensive equipment with less competition.
Refresh with: REFRESH MATERIALIZED VIEW analytics.super_tenders;';


-- ============================================================
-- REFRESH ALL VIEWS - Helper Function
-- ============================================================
CREATE OR REPLACE FUNCTION analytics.refresh_all_views()
RETURNS TABLE(view_name text, status text, duration interval) AS $$
DECLARE
    start_time timestamp;
    view_rec record;
BEGIN
    FOR view_rec IN
        SELECT matviewname
        FROM pg_matviews
        WHERE schemaname = 'analytics'
        ORDER BY matviewname
    LOOP
        start_time := clock_timestamp();

        BEGIN
            EXECUTE format('REFRESH MATERIALIZED VIEW analytics.%I', view_rec.matviewname);

            RETURN QUERY SELECT
                view_rec.matviewname::text,
                'SUCCESS'::text,
                clock_timestamp() - start_time;

        EXCEPTION WHEN OTHERS THEN
            RETURN QUERY SELECT
                view_rec.matviewname::text,
                'FAILED: ' || SQLERRM,
                clock_timestamp() - start_time;
        END;
    END LOOP;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION analytics.refresh_all_views() IS
'Refresh all materialized views in analytics schema.
Usage: SELECT * FROM analytics.refresh_all_views();';


-- ============================================================
-- USAGE INSTRUCTIONS
-- ============================================================

-- After running this file, refresh the views:
-- SELECT * FROM analytics.refresh_all_views();

-- Or refresh individual views:
-- REFRESH MATERIALIZED VIEW analytics.curativo_items;
-- REFRESH MATERIALIZED VIEW analytics.medical_items_summary;
-- REFRESH MATERIALIZED VIEW analytics.price_analysis;
-- REFRESH MATERIALIZED VIEW analytics.state_summary;
-- REFRESH MATERIALIZED VIEW analytics.top_winners;

-- For Looker Studio:
-- 1. Connect to your Cloud SQL database
-- 2. Select tables from the 'analytics' schema
-- 3. Each materialized view will appear as a regular table
-- 4. Recommended: Set up automated refresh (daily/weekly) via cron job

-- Automated refresh example (add to crontab):
-- 0 2 * * * psql -d medical_473219 -c "SELECT analytics.refresh_all_views();"
-- (Runs daily at 2 AM)
