-- Looker Studio Views for PNCP Medical Data Analysis
-- These views help you explore and filter tender items in Looker Studio
-- Connect Looker Studio to your Cloud SQL database and use these views

-- ============================================================================
-- VIEW 1: All Tender Items with Context
-- Complete view of all items with tender and organization details
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
    t.year,
    t.sequential_number,
    t.publication_date,
    t.state_code,
    t.municipality,
    t.total_homologated_value as tender_total_value,
    t.modality,
    t.status as tender_status,

    -- Organization details
    o.name as organization_name,
    o.cnpj as organization_cnpj,
    o.entity_type,

    -- Calculated fields
    CASE
        WHEN ti.homologated_unit_value > 0 THEN
            ROUND(((ti.estimated_unit_value - ti.homologated_unit_value) / ti.estimated_unit_value * 100)::numeric, 2)
        ELSE NULL
    END as savings_percent,

    CASE
        WHEN ti.homologated_total_value >= 100000 THEN 'High (>100k)'
        WHEN ti.homologated_total_value >= 50000 THEN 'Medium (50-100k)'
        WHEN ti.homologated_total_value >= 10000 THEN 'Low (10-50k)'
        ELSE 'Very Low (<10k)'
    END as value_category

FROM tender_items ti
JOIN tenders t ON ti.tender_id = t.id
JOIN organizations o ON t.organization_id = o.id
WHERE ti.homologated_unit_value IS NOT NULL;

-- ============================================================================
-- VIEW 2: Curativos (Dressings)
-- Filter for wound care products
-- ============================================================================
CREATE OR REPLACE VIEW vw_curativos AS
SELECT *
FROM vw_tender_items_complete
WHERE LOWER(item_description) LIKE '%curativo%'
   OR LOWER(item_description) LIKE '%bandagem%'
   OR LOWER(item_description) LIKE '%compressa%'
   OR LOWER(item_description) LIKE '%atadura%'
   OR LOWER(item_description) LIKE '%gaze%';

-- ============================================================================
-- VIEW 3: MDSAP Relevant Items
-- Filter for items matching your MDSAP product catalog
-- ============================================================================
CREATE OR REPLACE VIEW vw_mdsap_items AS
SELECT *
FROM vw_tender_items_complete
WHERE LOWER(item_description) LIKE '%transparente%'
   OR LOWER(item_description) LIKE '%filme%'
   OR LOWER(item_description) LIKE '%adesivo%'
   OR LOWER(item_description) LIKE '%semi permeavel%'
   OR LOWER(item_description) LIKE '%semipermeavel%';

-- ============================================================================
-- VIEW 4: High Value Items (>R$10k)
-- Focus on significant opportunities
-- ============================================================================
CREATE OR REPLACE VIEW vw_high_value_items AS
SELECT *
FROM vw_tender_items_complete
WHERE homologated_total_value >= 10000
ORDER BY homologated_total_value DESC;

-- ============================================================================
-- VIEW 5: Items by State
-- Aggregated view showing item counts and values by state
-- ============================================================================
CREATE OR REPLACE VIEW vw_items_by_state AS
SELECT
    state_code,
    COUNT(DISTINCT tender_id) as tender_count,
    COUNT(*) as item_count,
    SUM(homologated_total_value) as total_value,
    AVG(homologated_total_value) as avg_item_value,
    MIN(publication_date) as earliest_tender,
    MAX(publication_date) as latest_tender
FROM vw_tender_items_complete
GROUP BY state_code
ORDER BY total_value DESC;

-- ============================================================================
-- VIEW 6: Matched Products Performance
-- Shows your matched products with pricing comparisons
-- ============================================================================
CREATE OR REPLACE VIEW vw_matched_products_analysis AS
SELECT
    mp.id as match_id,
    mp.match_score,
    mp.price_difference_percent,
    mp.created_at as match_date,

    -- Fernandes product
    mp.fernandes_product_code,
    mp.fernandes_product_description,
    mp.moq,

    -- Tender item details
    ti.description as tender_item_description,
    ti.quantity,
    ti.unit,
    ti.homologated_unit_value as market_price,
    ti.homologated_total_value as market_total,

    -- Tender context
    t.control_number,
    t.state_code,
    t.publication_date,
    o.name as organization_name,

    -- Opportunity calculation
    CASE
        WHEN mp.price_difference_percent > 30 THEN 'High Opportunity'
        WHEN mp.price_difference_percent > 15 THEN 'Medium Opportunity'
        WHEN mp.price_difference_percent > 0 THEN 'Low Opportunity'
        ELSE 'No Opportunity'
    END as opportunity_level

FROM matched_products mp
JOIN tender_items ti ON mp.tender_item_id = ti.id
JOIN tenders t ON ti.tender_id = t.id
JOIN organizations o ON t.organization_id = o.id
ORDER BY mp.price_difference_percent DESC;

-- ============================================================================
-- VIEW 7: Monthly Trends
-- Track tender and item volumes over time
-- ============================================================================
CREATE OR REPLACE VIEW vw_monthly_trends AS
SELECT
    DATE_TRUNC('month', publication_date) as month,
    state_code,
    COUNT(DISTINCT tender_id) as tender_count,
    COUNT(*) as item_count,
    SUM(homologated_total_value) as total_value,
    AVG(homologated_total_value) as avg_item_value
FROM vw_tender_items_complete
GROUP BY DATE_TRUNC('month', publication_date), state_code
ORDER BY month DESC, total_value DESC;

-- ============================================================================
-- USAGE INSTRUCTIONS
-- ============================================================================
--
-- 1. Run this SQL file in your Cloud SQL database to create all views
-- 2. In Looker Studio, connect to your Cloud SQL database
-- 3. Select these views as data sources
-- 4. Create dashboards using these views
--
-- RECOMMENDED DASHBOARDS:
-- - Overview: Use vw_items_by_state and vw_monthly_trends
-- - Product Explorer: Use vw_curativos or vw_mdsap_items
-- - Opportunities: Use vw_matched_products_analysis
-- - High Value Tracking: Use vw_high_value_items
--
-- FILTERING IN LOOKER:
-- - By state_code (e.g., 'SP', 'RJ', 'RS')
-- - By publication_date (date range selector)
-- - By value_category (High, Medium, Low)
-- - By opportunity_level (for matched products)
--
-- CUSTOM KEYWORDS:
-- To add your own product filters, modify views like vw_mdsap_items:
--
-- CREATE OR REPLACE VIEW vw_my_products AS
-- SELECT * FROM vw_tender_items_complete
-- WHERE LOWER(item_description) LIKE '%your_keyword%'
--    OR LOWER(item_description) LIKE '%another_keyword%';
