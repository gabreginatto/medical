-- Organizations table
CREATE TABLE IF NOT EXISTS organizations (
    id SERIAL PRIMARY KEY,
    cnpj VARCHAR(18) UNIQUE NOT NULL,
    name VARCHAR(500) NOT NULL,
    government_level VARCHAR(50) NOT NULL,
    organization_type VARCHAR(50),
    state_code VARCHAR(2),
    municipality_name VARCHAR(200),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tenders table
CREATE TABLE IF NOT EXISTS tenders (
    id SERIAL PRIMARY KEY,
    organization_id INTEGER REFERENCES organizations(id),
    cnpj VARCHAR(18) NOT NULL,
    ano INTEGER NOT NULL,
    sequencial INTEGER NOT NULL,
    control_number VARCHAR(50) UNIQUE,
    title VARCHAR(1000),
    description TEXT,
    government_level VARCHAR(50) NOT NULL,
    tender_size VARCHAR(20) NOT NULL,
    contracting_modality INTEGER,
    modality_name VARCHAR(100),
    total_estimated_value DECIMAL(15,2),
    total_homologated_value DECIMAL(15,2),
    publication_date DATE,
    state_code VARCHAR(2),
    municipality_code VARCHAR(10),
    status VARCHAR(50),
    process_category INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(cnpj, ano, sequencial)
);

-- Tender items table
CREATE TABLE IF NOT EXISTS tender_items (
    id SERIAL PRIMARY KEY,
    tender_id INTEGER REFERENCES tenders(id),
    item_number INTEGER NOT NULL,
    description TEXT NOT NULL,
    unit VARCHAR(20),
    quantity DECIMAL(12,3),
    estimated_unit_value DECIMAL(12,4),
    estimated_total_value DECIMAL(15,2),
    homologated_unit_value DECIMAL(12,4),
    homologated_total_value DECIMAL(15,2),
    winner_name VARCHAR(500),
    winner_cnpj VARCHAR(18),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(tender_id, item_number)
);

-- Matched products table
CREATE TABLE IF NOT EXISTS matched_products (
    id SERIAL PRIMARY KEY,
    tender_item_id INTEGER REFERENCES tender_items(id),
    fernandes_product_code VARCHAR(50) NOT NULL,
    fernandes_product_description VARCHAR(500) NOT NULL,
    match_score DECIMAL(5,2) NOT NULL,
    fob_price_usd DECIMAL(10,4),
    moq INTEGER,
    price_comparison_brl DECIMAL(10,4),
    price_comparison_usd DECIMAL(10,4),
    exchange_rate DECIMAL(8,4),
    price_difference_percent DECIMAL(6,2),
    is_competitive BOOLEAN,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(tender_item_id, fernandes_product_code)
);

-- Processing log table
CREATE TABLE IF NOT EXISTS processing_log (
    id SERIAL PRIMARY KEY,
    process_type VARCHAR(50) NOT NULL,
    state_code VARCHAR(2),
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,
    status VARCHAR(20) NOT NULL,
    records_processed INTEGER DEFAULT 0,
    records_matched INTEGER DEFAULT 0,
    error_message TEXT,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Homologated results table
CREATE TABLE IF NOT EXISTS homologated_results (
    id SERIAL PRIMARY KEY,
    tender_item_id INTEGER REFERENCES tender_items(id),
    result_sequential INTEGER NOT NULL,
    supplier_name VARCHAR(500),
    supplier_cnpj VARCHAR(18),
    bid_value DECIMAL(15,2),
    is_winner BOOLEAN DEFAULT FALSE,
    ranking_position INTEGER,
    bid_date TIMESTAMP,
    additional_data JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(tender_item_id, result_sequential)
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_organizations_cnpj ON organizations(cnpj);
CREATE INDEX IF NOT EXISTS idx_organizations_state ON organizations(state_code);
CREATE INDEX IF NOT EXISTS idx_organizations_gov_level ON organizations(government_level);

CREATE INDEX IF NOT EXISTS idx_tenders_cnpj_ano_seq ON tenders(cnpj, ano, sequencial);
CREATE INDEX IF NOT EXISTS idx_tenders_state ON tenders(state_code);
CREATE INDEX IF NOT EXISTS idx_tenders_gov_level ON tenders(government_level);
CREATE INDEX IF NOT EXISTS idx_tenders_publication_date ON tenders(publication_date);
CREATE INDEX IF NOT EXISTS idx_tenders_homologated_value ON tenders(total_homologated_value);

CREATE INDEX IF NOT EXISTS idx_tender_items_tender_id ON tender_items(tender_id);
CREATE INDEX IF NOT EXISTS idx_tender_items_item_number ON tender_items(item_number);

CREATE INDEX IF NOT EXISTS idx_matched_products_tender_item_id ON matched_products(tender_item_id);
CREATE INDEX IF NOT EXISTS idx_matched_products_fernandes_code ON matched_products(fernandes_product_code);
CREATE INDEX IF NOT EXISTS idx_matched_products_match_score ON matched_products(match_score);

CREATE INDEX IF NOT EXISTS idx_processing_log_process_type ON processing_log(process_type);
CREATE INDEX IF NOT EXISTS idx_processing_log_state ON processing_log(state_code);
CREATE INDEX IF NOT EXISTS idx_processing_log_status ON processing_log(status);

CREATE INDEX IF NOT EXISTS idx_homologated_results_tender_item ON homologated_results(tender_item_id);
CREATE INDEX IF NOT EXISTS idx_homologated_results_winner ON homologated_results(is_winner);