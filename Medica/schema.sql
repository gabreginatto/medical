-- MEDICA Exhibitors Database Schema
-- Run this in your Cloud SQL PostgreSQL instance

-- Drop tables if they exist (for fresh start)
DROP TABLE IF EXISTS medica_documents CASCADE;
DROP TABLE IF EXISTS medica_product_images CASCADE;
DROP TABLE IF EXISTS medica_exhibitors CASCADE;

-- Main exhibitors table
CREATE TABLE medica_exhibitors (
    id SERIAL PRIMARY KEY,
    name VARCHAR(500) NOT NULL,
    location VARCHAR(200),
    company_description TEXT,
    email VARCHAR(255),
    phone VARCHAR(100),
    website VARCHAR(500),
    address TEXT,
    raw_text TEXT,
    country VARCHAR(100),
    region VARCHAR(50),
    event VARCHAR(100) DEFAULT 'MEDICA 2025',
    scraped_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Product images table (references Cloud Storage URLs)
CREATE TABLE medica_product_images (
    id SERIAL PRIMARY KEY,
    exhibitor_id INTEGER NOT NULL REFERENCES medica_exhibitors(id) ON DELETE CASCADE,
    image_filename VARCHAR(255) NOT NULL,
    gcs_url VARCHAR(1000),
    gcs_bucket VARCHAR(255),
    gcs_path VARCHAR(500),
    image_order INTEGER,
    file_size_bytes BIGINT,
    uploaded_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT unique_exhibitor_image UNIQUE(exhibitor_id, image_filename)
);

-- Documents table (PDFs, etc.)
CREATE TABLE medica_documents (
    id SERIAL PRIMARY KEY,
    exhibitor_id INTEGER NOT NULL REFERENCES medica_exhibitors(id) ON DELETE CASCADE,
    document_filename VARCHAR(255) NOT NULL,
    gcs_url VARCHAR(1000),
    gcs_bucket VARCHAR(255),
    gcs_path VARCHAR(500),
    file_size_bytes BIGINT,
    uploaded_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT unique_exhibitor_document UNIQUE(exhibitor_id, document_filename)
);

-- Create indexes for better query performance
CREATE INDEX idx_exhibitors_name ON medica_exhibitors(name);
CREATE INDEX idx_exhibitors_event ON medica_exhibitors(event);
CREATE INDEX idx_exhibitors_scraped_at ON medica_exhibitors(scraped_at);
CREATE INDEX idx_product_images_exhibitor ON medica_product_images(exhibitor_id);
CREATE INDEX idx_documents_exhibitor ON medica_documents(exhibitor_id);

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Add trigger to auto-update updated_at
CREATE TRIGGER update_medica_exhibitors_updated_at
    BEFORE UPDATE ON medica_exhibitors
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Grant permissions (adjust user as needed)
-- GRANT ALL PRIVILEGES ON TABLE medica_exhibitors TO your_user;
-- GRANT ALL PRIVILEGES ON TABLE medica_product_images TO your_user;
-- GRANT ALL PRIVILEGES ON TABLE medica_documents TO your_user;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO your_user;

-- Sample query to verify setup
-- SELECT
--     e.name,
--     e.location,
--     COUNT(p.id) as num_images,
--     COUNT(d.id) as num_docs
-- FROM medica_exhibitors e
-- LEFT JOIN medica_product_images p ON e.id = p.exhibitor_id
-- LEFT JOIN medica_documents d ON e.id = d.exhibitor_id
-- GROUP BY e.id, e.name, e.location;
