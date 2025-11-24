-- ============================================================================
-- UNIFIED MEDICAL EXHIBITORS DATABASE - NEW DATABASE CREATION
-- ============================================================================
-- Purpose: Create new unified database for MEDICA and CMEF data
-- Safety: Does NOT modify existing medical database
-- Date: 2025-11-23
-- ============================================================================

-- Step 1: Create new database (run as postgres superuser)
-- ============================================================================
-- Note: Uncomment and run separately if creating new database
-- CREATE DATABASE medical_unified;
-- \c medical_unified

-- ============================================================================
-- Step 2: Create unified exhibitors table with all features
-- ============================================================================

CREATE TABLE IF NOT EXISTS medical_exhibitors (
    -- Primary Key
    id SERIAL PRIMARY KEY,

    -- Basic Company Information (from both MEDICA and CMEF)
    name VARCHAR(500) NOT NULL,                    -- English company name
    company_name_zh VARCHAR(500),                  -- Chinese company name (CMEF)
    location VARCHAR(200),                         -- Hall location (MEDICA) or city (CMEF)
    booth_number VARCHAR(50),                      -- Exhibition booth number

    -- Contact Information
    email VARCHAR(255),
    phone VARCHAR(100),
    website VARCHAR(500),
    address TEXT,
    country VARCHAR(100),
    region VARCHAR(50),

    -- Event Tracking
    event VARCHAR(100) NOT NULL,                   -- e.g., "MEDICA 2025", "CMEF 2025"
    data_source VARCHAR(50) NOT NULL,              -- "MEDICA" or "CMEF"

    -- Company Description
    company_description TEXT,                      -- Full company/product description
    raw_text TEXT,                                 -- Original raw OCR text (MEDICA)

    -- AI Product Classification (NEW - from CMEF enhancement)
    product_category VARCHAR(200),                 -- e.g., "Orthopedics & Rehabilitation"
    product_keywords TEXT[],                       -- Searchable keywords array
    category_confidence FLOAT,                     -- AI classification confidence (0.0-1.0)

    -- Website Validation (NEW - from CMEF enhancement)
    website_validated BOOLEAN DEFAULT FALSE,       -- Whether website was checked
    website_status_code INTEGER,                   -- HTTP status code (200 = OK)

    -- Timestamps
    scraped_at TIMESTAMP,                          -- When data was scraped
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    -- Constraints
    CONSTRAINT unique_company_event UNIQUE(name, event)
);

-- ============================================================================
-- Step 3: Create indexes for performance
-- ============================================================================

-- Basic search indexes
CREATE INDEX idx_exhibitors_name ON medical_exhibitors(name);
CREATE INDEX idx_exhibitors_country ON medical_exhibitors(country);
CREATE INDEX idx_exhibitors_event ON medical_exhibitors(event);
CREATE INDEX idx_exhibitors_data_source ON medical_exhibitors(data_source);

-- Product search indexes (NEW)
CREATE INDEX idx_exhibitors_category ON medical_exhibitors(product_category);
CREATE INDEX idx_exhibitors_booth ON medical_exhibitors(booth_number);
CREATE INDEX idx_exhibitors_website_validated ON medical_exhibitors(website_validated);

-- GIN index for keyword array search (PostgreSQL array search)
CREATE INDEX idx_exhibitors_keywords ON medical_exhibitors USING GIN(product_keywords);

-- Full-text search indexes
CREATE INDEX idx_exhibitors_description ON medical_exhibitors USING GIN(to_tsvector('english', company_description));

-- Composite indexes for common queries
CREATE INDEX idx_exhibitors_source_event ON medical_exhibitors(data_source, event);
CREATE INDEX idx_exhibitors_category_source ON medical_exhibitors(product_category, data_source);

-- ============================================================================
-- Step 4: Create views for backward compatibility
-- ============================================================================

-- View for MEDICA data only (mimics old medica_exhibitors table)
CREATE OR REPLACE VIEW medica_exhibitors AS
SELECT
    id,
    name,
    location,
    company_description,
    email,
    phone,
    website,
    address,
    raw_text,
    country,
    region,
    event,
    scraped_at,
    created_at,
    updated_at,
    -- New fields
    company_name_zh,
    booth_number,
    product_category,
    product_keywords,
    category_confidence,
    website_validated,
    website_status_code
FROM medical_exhibitors
WHERE data_source = 'MEDICA';

-- View for CMEF data only
CREATE OR REPLACE VIEW cmef_exhibitors AS
SELECT
    id,
    name,
    company_name_zh,
    booth_number,
    company_description,
    email,
    phone,
    website,
    address,
    country,
    region,
    event,
    product_category,
    product_keywords,
    category_confidence,
    website_validated,
    website_status_code,
    scraped_at,
    created_at,
    updated_at
FROM medical_exhibitors
WHERE data_source = 'CMEF';

-- ============================================================================
-- Step 5: Add helpful comments
-- ============================================================================

COMMENT ON TABLE medical_exhibitors IS 'Unified catalog of medical equipment exhibitors from MEDICA and CMEF trade shows';

COMMENT ON COLUMN medical_exhibitors.name IS 'English company name (primary identifier)';
COMMENT ON COLUMN medical_exhibitors.company_name_zh IS 'Chinese company name (for CMEF and Chinese MEDICA companies)';
COMMENT ON COLUMN medical_exhibitors.booth_number IS 'Exhibition booth number (e.g., "5.2H25" for CMEF, "Hall 16 A03" for MEDICA)';
COMMENT ON COLUMN medical_exhibitors.product_category IS 'AI-classified product category (e.g., "Orthopedics & Rehabilitation")';
COMMENT ON COLUMN medical_exhibitors.product_keywords IS 'Searchable product keywords array (e.g., {wheelchair, "hospital bed", crutches})';
COMMENT ON COLUMN medical_exhibitors.category_confidence IS 'AI classification confidence score (0.0 - 1.0)';
COMMENT ON COLUMN medical_exhibitors.website_validated IS 'Whether website was validated via HTTP check';
COMMENT ON COLUMN medical_exhibitors.website_status_code IS 'HTTP status code from website validation (200 = OK)';
COMMENT ON COLUMN medical_exhibitors.data_source IS 'Data source identifier: "MEDICA" or "CMEF"';
COMMENT ON COLUMN medical_exhibitors.event IS 'Event name and year (e.g., "MEDICA 2025", "CMEF 2025")';

-- ============================================================================
-- Step 6: Create helper functions
-- ============================================================================

-- Function to update updated_at timestamp automatically
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to auto-update updated_at
CREATE TRIGGER update_medical_exhibitors_updated_at
    BEFORE UPDATE ON medical_exhibitors
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- Check table structure
SELECT
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'medical_exhibitors'
ORDER BY ordinal_position;

-- Check indexes
SELECT
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename = 'medical_exhibitors'
ORDER BY indexname;

-- ============================================================================
-- EXAMPLE QUERIES
-- ============================================================================

-- Example 1: Search for orthopedic products across both catalogs
-- SELECT name, data_source, event, product_category, product_keywords, website
-- FROM medical_exhibitors
-- WHERE product_category = 'Orthopedics & Rehabilitation'
-- ORDER BY category_confidence DESC;

-- Example 2: Find companies selling wheelchairs
-- SELECT name, data_source, event, location, booth_number, website
-- FROM medical_exhibitors
-- WHERE 'wheelchair' = ANY(product_keywords)
--    OR company_description ILIKE '%wheelchair%';

-- Example 3: Compare MEDICA vs CMEF by category
-- SELECT
--     product_category,
--     COUNT(*) FILTER (WHERE data_source = 'MEDICA') as medica_count,
--     COUNT(*) FILTER (WHERE data_source = 'CMEF') as cmef_count,
--     COUNT(*) as total_count
-- FROM medical_exhibitors
-- WHERE product_category IS NOT NULL
-- GROUP BY product_category
-- ORDER BY total_count DESC;

-- Example 4: Full-text search across descriptions
-- SELECT name, data_source, product_category, website
-- FROM medical_exhibitors
-- WHERE to_tsvector('english', company_description) @@ to_tsquery('english', 'ultrasound & imaging');

-- ============================================================================
-- NEXT STEPS
-- ============================================================================
-- 1. Create new Cloud SQL database: gcloud sql databases create medical_unified --instance=<instance-name>
-- 2. Run this script: psql -h <host> -U postgres -d medical_unified -f create_unified_database.sql
-- 3. Run migration: python3 migrate_medica_to_unified.py (copies old MEDICA data)
-- 4. Import CMEF: python3 import_cmef_to_unified.py (adds CMEF companies)
-- 5. Classify all: python3 classify_unified_companies.py (enriches both datasets)
-- 6. Update Looker connection to point to new database
