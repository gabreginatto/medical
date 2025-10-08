-- ============================================================================
-- LOOKER STUDIO VIEWS FOR PNCP MEDICAL DATA ANALYSIS
-- ============================================================================
-- Purpose: Create optimized views for Looker Studio dashboards
--
-- INSTRUCTIONS:
-- 1. Connect to your Cloud SQL database
-- 2. Run this entire file: psql -h <host> -U postgres -d pncp_medical_data -f looker_views.sql
-- 3. Connect Looker Studio to these views
--
-- Note: These are regular views (not materialized) for real-time data in Looker
-- ============================================================================

-- ============================================================================
-- VIEW 1: All Tender Items with Complete Context
-- Base view with all items and full tender/organization details
-- ============================================================================
CREATE OR REPLACE VIEW vw_tender_items_complete AS
SELECT
    -- Item details
    ti.id as item_id,
    ti.item_number,
    ti.description as item_description,
    ti.unit,
    ti.quantity,
    ti.estimated_unit_value,
    ti.estimated_total_value,
    ti.homologated_unit_value,
    ti.homologated_total_value,
    ti.winner_name,
    ti.winner_cnpj,
    ti.catmat_codes,
    ti.has_medical_catmat,
    ti.created_at as item_created_at,

    -- Tender details
    t.id as tender_id,
    t.control_number,
    t.year as tender_year,
    t.sequential_number,
    t.publication_date,
    t.state_code,
    t.total_homologated_value as tender_total_value,
    t.modality_code,

    -- Organization details
    o.name as organization_name,
    o.cnpj as organization_cnpj,
    o.government_level,
    o.organization_type,

    -- Calculated fields
    CASE
        WHEN ti.estimated_unit_value > 0 AND ti.homologated_unit_value > 0 THEN
            ROUND(((ti.estimated_unit_value - ti.homologated_unit_value) / ti.estimated_unit_value * 100)::numeric, 2)
        ELSE NULL
    END as savings_percent,

    CASE
        WHEN ti.homologated_total_value >= 100000 THEN 'High (>100k)'
        WHEN ti.homologated_total_value >= 50000 THEN 'Medium (50-100k)'
        WHEN ti.homologated_total_value >= 10000 THEN 'Low (10-50k)'
        ELSE 'Very Low (<10k)'
    END as item_value_category

FROM tender_items ti
JOIN tenders t ON ti.tender_id = t.id
JOIN organizations o ON t.organization_id = o.id
WHERE ti.homologated_unit_value IS NOT NULL;

COMMENT ON VIEW vw_tender_items_complete IS
'Complete view of all tender items with full context. Use as base for Looker Studio reports.';

-- ============================================================================
-- VIEW 2: Curativos (Wound Care Products)
-- Filter for wound care items: curativos, bandagens, malha tubular
-- ============================================================================
CREATE OR REPLACE VIEW vw_curativos AS
SELECT *
FROM vw_tender_items_complete
WHERE LOWER(item_description) LIKE '%curativ%'
   OR LOWER(item_description) LIKE '%bandag%'
   OR LOWER(item_description) LIKE '%malha tubular%';

COMMENT ON VIEW vw_curativos IS
'Filtered view for wound care products: curativos, bandagens, malha tubular. Use for category-specific analysis in Looker.';

-- ============================================================================
-- VIEW 3: MDSAP Relevant Items
-- Filter for items matching MDSAP product catalog keywords
-- ============================================================================
CREATE OR REPLACE VIEW vw_mdsap_items AS
SELECT *
FROM vw_tender_items_complete
WHERE LOWER(item_description) LIKE '%transparente%'
   OR LOWER(item_description) LIKE '%filme%'
   OR LOWER(item_description) LIKE '%adesivo%'
   OR LOWER(item_description) LIKE '%semi permeavel%'
   OR LOWER(item_description) LIKE '%semipermeavel%';

COMMENT ON VIEW vw_mdsap_items IS
'Filtered view for MDSAP-relevant products. Update keywords in WHERE clause to match your product catalog.';

-- ============================================================================
-- VIEW 4: High Value Tenders
-- Tenders worth >R$20 million with ≤10 items (high-value, low-complexity)
-- ============================================================================
CREATE OR REPLACE VIEW vw_high_value_items AS
WITH tender_item_counts AS (
    SELECT
        tender_id,
        COUNT(*) as item_count
    FROM tender_items
    WHERE homologated_total_value > 0
    GROUP BY tender_id
)
SELECT
    ti.*,
    tic.item_count as tender_item_count,
    ROUND((ti.tender_total_value / tic.item_count)::numeric, 2) as avg_value_per_item,
    CASE
        WHEN ti.tender_total_value >= 50000000 THEN 'Mega (>R$50M)'
        WHEN ti.tender_total_value >= 30000000 THEN 'Very High (R$30-50M)'
        WHEN ti.tender_total_value >= 20000000 THEN 'High (R$20-30M)'
        ELSE 'Other'
    END as tender_value_category
FROM vw_tender_items_complete ti
JOIN tender_item_counts tic ON ti.tender_id = tic.tender_id
WHERE ti.tender_total_value >= 20000000  -- Tenders >R$20M
  AND tic.item_count <= 10;              -- With ≤10 items

COMMENT ON VIEW vw_high_value_items IS
'High-value tenders (>R$20M) with low item count (≤10 items). These represent focused, high-value opportunities with less competition.';

-- ============================================================================
-- VIEW 5: Items by State (Geographic Breakdown)
-- Aggregated statistics by state for geographic analysis
-- ============================================================================
CREATE OR REPLACE VIEW vw_items_by_state AS
SELECT
    state_code,
    COUNT(DISTINCT tender_id) as tender_count,
    COUNT(DISTINCT organization_name) as organization_count,
    COUNT(*) as item_count,
    SUM(homologated_total_value) as total_value_brl,
    AVG(homologated_total_value) as avg_item_value_brl,
    MIN(homologated_total_value) as min_item_value_brl,
    MAX(homologated_total_value) as max_item_value_brl,
    MIN(publication_date) as earliest_tender_date,
    MAX(publication_date) as latest_tender_date,
    -- High-value tender count
    COUNT(DISTINCT tender_id) FILTER (WHERE tender_total_value >= 20000000) as high_value_tender_count,
    -- Average items per tender
    ROUND(COUNT(*)::numeric / COUNT(DISTINCT tender_id), 2) as avg_items_per_tender
FROM vw_tender_items_complete
GROUP BY state_code
ORDER BY total_value_brl DESC;

COMMENT ON VIEW vw_items_by_state IS
'Geographic breakdown of tenders and items by state. Use for state-level dashboards and comparison analysis in Looker.';

-- ============================================================================
-- VIEW 6: Matched Products Analysis (Optional - for AI matching results)
-- Shows matched products with pricing comparisons when ai_matching/ is run
-- ============================================================================
CREATE OR REPLACE VIEW vw_matched_products_analysis AS
SELECT
    mp.id as match_id,
    mp.similarity_score as match_confidence,
    mp.product_code,
    mp.created_at as match_date,

    -- Tender item details
    ti.description as tender_item_description,
    ti.quantity,
    ti.unit,
    ti.homologated_unit_value as market_price_brl,
    ti.homologated_total_value as market_total_brl,
    ti.winner_name,

    -- Tender context
    t.control_number,
    t.state_code,
    t.publication_date,
    o.name as organization_name

FROM matched_products mp
JOIN tender_items ti ON mp.item_id = ti.id
JOIN tenders t ON ti.tender_id = t.id
JOIN organizations o ON t.organization_id = o.id
ORDER BY mp.similarity_score DESC;

COMMENT ON VIEW vw_matched_products_analysis IS
'Analysis of matched products from ai_matching/ module. Shows pricing comparisons and savings opportunities. Only populated after running AI matching.';

-- ============================================================================
-- USAGE INSTRUCTIONS FOR LOOKER STUDIO
-- ============================================================================
--
-- SETUP:
-- 1. Connect to Cloud SQL: psql -h <host> -U postgres -d pncp_medical_data
-- 2. Run this file: \i looker_views.sql
-- 3. Verify views created: \dv
-- 4. In Looker Studio, connect to your Cloud SQL database
-- 5. Select these views as data sources
--
-- VIEWS CREATED:
-- 1. vw_tender_items_complete   - Base view with all items + context
-- 2. vw_curativos                - Wound care products filter
-- 3. vw_mdsap_items              - MDSAP product filter
-- 4. vw_high_value_items         - High-value tenders (>R$20M, ≤10 items)
-- 5. vw_items_by_state           - Geographic aggregation
-- 6. vw_matched_products_analysis - AI matching results (optional)
--
-- RECOMMENDED DASHBOARDS:
-- - Overview Dashboard:
--   * Use vw_items_by_state for geographic heatmap
--   * Filter by publication_date for time range
--   * Show tender_count, total_value_brl metrics
--
-- - Product Explorer:
--   * Use vw_curativos or vw_mdsap_items
--   * Group by item_description for product breakdown
--   * Filter by state_code for regional analysis
--
-- - High-Value Opportunities:
--   * Use vw_high_value_items
--   * Sort by tender_total_value DESC
--   * Filter by tender_value_category
--
-- - Matched Products (after running ai_matching/):
--   * Use vw_matched_products_analysis
--   * Filter by opportunity_level = 'High Opportunity'
--   * Show potential_savings_brl sum
--
-- FILTERING OPTIONS IN LOOKER:
-- - state_code: 'SP', 'RJ', 'MG', 'RS', etc.
-- - publication_date: Date range selector
-- - tender_year: 2024, 2025, etc.
-- - item_value_category: 'High', 'Medium', 'Low', 'Very Low'
-- - tender_value_category: 'Mega', 'Very High', 'High'
-- - government_level: 'Federal', 'Estadual', 'Municipal'
-- - opportunity_level: 'High Opportunity', 'Medium Opportunity', 'Low Opportunity'
--
-- CUSTOMIZATION:
-- To add your own product filters, create new views:
--
-- Example - Create custom filter view:
-- CREATE OR REPLACE VIEW vw_my_products AS
-- SELECT * FROM vw_tender_items_complete
-- WHERE LOWER(item_description) LIKE '%your_keyword%'
--    OR LOWER(item_description) LIKE '%another_keyword%';
--
-- Example - Add state filter to existing view:
-- CREATE OR REPLACE VIEW vw_curativos_sp AS
-- SELECT * FROM vw_curativos
-- WHERE state_code = 'SP';
--
-- PERFORMANCE TIPS:
-- - Views are not materialized (real-time data)
-- - For better performance with large datasets, consider adding WHERE filters
-- - Use date range filters in Looker to limit data scanned
-- - Indexes on base tables will speed up view queries
--
-- REFRESH:
-- Views are automatically updated as base tables change (not cached).
-- No manual refresh needed.
