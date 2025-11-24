-- ============================================================================
-- UNIFIED MEDICAL EXHIBITORS DATABASE - MIGRATION SCRIPT
-- ============================================================================
-- Purpose: Extend medica_exhibitors to support both MEDICA and CMEF data
-- Date: 2025-11-23
-- ============================================================================

-- Step 1: Add new columns to existing medica_exhibitors table
-- ============================================================================

ALTER TABLE medica_exhibitors
ADD COLUMN IF NOT EXISTS company_name_zh VARCHAR(500),
ADD COLUMN IF NOT EXISTS booth_number VARCHAR(50),
ADD COLUMN IF NOT EXISTS product_category VARCHAR(200),
ADD COLUMN IF NOT EXISTS product_keywords TEXT[],
ADD COLUMN IF NOT EXISTS category_confidence FLOAT,
ADD COLUMN IF NOT EXISTS website_validated BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS website_status_code INTEGER,
ADD COLUMN IF NOT EXISTS data_source VARCHAR(50) DEFAULT 'MEDICA';  -- NEW: Track data source

-- Step 2: Update existing MEDICA records to have data_source = 'MEDICA'
-- ============================================================================

UPDATE medica_exhibitors
SET data_source = 'MEDICA'
WHERE data_source IS NULL;

-- Step 3: Create indexes for new fields
-- ============================================================================

-- GIN index for keyword array search (PostgreSQL)
CREATE INDEX IF NOT EXISTS idx_medica_keywords ON medica_exhibitors USING GIN(product_keywords);

-- Regular indexes for filtering
CREATE INDEX IF NOT EXISTS idx_medica_category ON medica_exhibitors(product_category);
CREATE INDEX IF NOT EXISTS idx_medica_data_source ON medica_exhibitors(data_source);
CREATE INDEX IF NOT EXISTS idx_medica_booth ON medica_exhibitors(booth_number);
CREATE INDEX IF NOT EXISTS idx_medica_website_validated ON medica_exhibitors(website_validated);

-- Step 4: Add comments for documentation
-- ============================================================================

COMMENT ON COLUMN medica_exhibitors.company_name_zh IS 'Chinese company name (for CMEF and Chinese MEDICA companies)';
COMMENT ON COLUMN medica_exhibitors.booth_number IS 'Exhibition booth number (e.g., "5.2H25" for CMEF, "Hall 16 A03" for MEDICA)';
COMMENT ON COLUMN medica_exhibitors.product_category IS 'AI-classified product category (e.g., "Orthopedics & Rehabilitation")';
COMMENT ON COLUMN medica_exhibitors.product_keywords IS 'Searchable product keywords array (e.g., {wheelchair, "hospital bed", crutches})';
COMMENT ON COLUMN medica_exhibitors.category_confidence IS 'AI classification confidence score (0.0 - 1.0)';
COMMENT ON COLUMN medica_exhibitors.website_validated IS 'Whether website was validated via HTTP check';
COMMENT ON COLUMN medica_exhibitors.website_status_code IS 'HTTP status code from website validation (200 = OK)';
COMMENT ON COLUMN medica_exhibitors.data_source IS 'Data source identifier: "MEDICA" or "CMEF"';

-- Step 5: Rename table to reflect unified purpose (optional)
-- ============================================================================
-- UNCOMMENT to rename table to medical_exhibitors
-- ALTER TABLE medica_exhibitors RENAME TO medical_exhibitors;
-- Note: If renamed, update all views, Looker configs, and application code

-- Step 6: Create view for backward compatibility (if table is renamed)
-- ============================================================================
-- CREATE OR REPLACE VIEW medica_exhibitors AS
-- SELECT * FROM medical_exhibitors WHERE data_source = 'MEDICA';

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- Check schema changes
SELECT
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'medica_exhibitors'
    AND column_name IN (
        'company_name_zh', 'booth_number', 'product_category',
        'product_keywords', 'category_confidence', 'website_validated',
        'website_status_code', 'data_source'
    )
ORDER BY ordinal_position;

-- Count existing records by source
SELECT
    data_source,
    COUNT(*) as total_companies,
    COUNT(product_category) as classified_companies,
    COUNT(product_keywords) FILTER (WHERE array_length(product_keywords, 1) > 0) as companies_with_keywords,
    AVG(category_confidence) as avg_confidence
FROM medica_exhibitors
GROUP BY data_source;

-- ============================================================================
-- USAGE EXAMPLES
-- ============================================================================

-- Example 1: Search for orthopedic products across both catalogs
-- SELECT name, data_source, event, product_category, product_keywords
-- FROM medica_exhibitors
-- WHERE product_category = 'Orthopedics & Rehabilitation'
-- ORDER BY category_confidence DESC;

-- Example 2: Find companies selling specific products
-- SELECT name, data_source, event, location, website
-- FROM medica_exhibitors
-- WHERE 'wheelchair' = ANY(product_keywords)
--    OR 'crutches' = ANY(product_keywords);

-- Example 3: Compare MEDICA vs CMEF by category
-- SELECT
--     product_category,
--     COUNT(*) FILTER (WHERE data_source = 'MEDICA') as medica_count,
--     COUNT(*) FILTER (WHERE data_source = 'CMEF') as cmef_count,
--     COUNT(*) as total_count
-- FROM medica_exhibitors
-- GROUP BY product_category
-- ORDER BY total_count DESC;

-- ============================================================================
-- NEXT STEPS
-- ============================================================================
-- 1. Run this migration: psql -h <host> -U postgres -d medical -f migrate_unified_schema.sql
-- 2. Classify existing MEDICA companies: python3 classify_medica_companies.py
-- 3. Import CMEF companies: python3 import_cmef_to_medica.py
-- 4. Update Looker views to include new dimensions
-- 5. Create unified dashboards with data_source filter
