"""
GCP Cloud SQL (PostgreSQL) database module for PNCP medical data processing
Handles database connections, schema creation, and data operations
"""

import os
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import asyncio
import asyncpg
from google.cloud.sql.connector import Connector
import sqlalchemy
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from config import DatabaseConfig, GovernmentLevel, TenderSize, OrganizationType

logger = logging.getLogger(__name__)

class CloudSQLManager:
    """Manages connections and operations for GCP Cloud SQL PostgreSQL"""

    def __init__(self, project_id: str, region: str, instance_name: str, database_name: str = None):
        self.project_id = project_id
        self.region = region
        self.instance_name = instance_name
        self.database_name = database_name or DatabaseConfig.DATABASE_NAME
        self.connection_name = f"{project_id}:{region}:{instance_name}"

        self.connector = Connector()
        self.engine = None
        self.async_engine = None

    def get_connection_string(self, use_async: bool = False) -> str:
        """Generate connection string for Cloud SQL"""
        if DatabaseConfig.USE_IAM_AUTH:
            # Use IAM authentication
            if use_async:
                return f"postgresql+asyncpg://{self.database_name}"
            else:
                return f"postgresql+pg8000://{self.database_name}"
        else:
            # Use username/password (for development/testing)
            user = os.getenv('DB_USER', 'postgres')
            password = os.getenv('DB_PASSWORD', '')
            if use_async:
                return f"postgresql+asyncpg://{user}:{password}@/{self.database_name}"
            else:
                return f"postgresql+pg8000://{user}:{password}@/{self.database_name}"

    async def get_connection(self):
        """Get async database connection using Cloud SQL connector"""
        # For IAM auth, user should be the service account email or use default 'postgres'
        # For now, we'll use regular postgres user with password
        db_user = os.getenv('DB_USER', 'postgres')
        db_password = os.getenv('DB_PASSWORD', '')

        connection_params = {
            'instance_connection_string': self.connection_name,
            'driver': "asyncpg",
            'user': db_user,
            'db': self.database_name,  # Cloud SQL Connector uses 'db' parameter
            'ip_type': "private" if os.getenv('USE_PRIVATE_IP', 'true').lower() == 'true' else "public"
        }

        # Only add password if not using IAM auth
        if not DatabaseConfig.USE_IAM_AUTH and db_password:
            connection_params['password'] = db_password

        if DatabaseConfig.USE_IAM_AUTH:
            connection_params['enable_iam_auth'] = True

        return await self.connector.connect_async(**connection_params)

    def create_sync_engine(self):
        """Create synchronous SQLAlchemy engine"""
        if self.engine is None:
            self.engine = create_engine(
                self.get_connection_string(use_async=False),
                creator=self._get_sync_connection,
                pool_size=DatabaseConfig.MAX_CONNECTIONS,
                pool_timeout=DatabaseConfig.CONNECTION_TIMEOUT,
                echo=False  # Set to True for SQL debugging
            )
        return self.engine

    def create_async_engine(self):
        """Create asynchronous SQLAlchemy engine"""
        if self.async_engine is None:
            self.async_engine = create_async_engine(
                self.get_connection_string(use_async=True),
                creator=self._get_async_connection,
                pool_size=DatabaseConfig.MAX_CONNECTIONS,
                pool_timeout=DatabaseConfig.CONNECTION_TIMEOUT,
                echo=False  # Set to True for SQL debugging
            )
        return self.async_engine

    def _get_sync_connection(self):
        """Get synchronous connection for SQLAlchemy"""
        # This would need to be implemented based on your specific Cloud SQL setup
        # For now, using standard asyncpg connection
        pass

    async def _get_async_connection(self):
        """Get asynchronous connection for SQLAlchemy"""
        return await self.get_connection()

    async def close(self):
        """Close connector and engines"""
        if self.async_engine:
            await self.async_engine.dispose()
        if self.engine:
            self.engine.dispose()
        await self.connector.close_async()

# Database schema SQL
DATABASE_SCHEMA = """
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

-- Tender items table (V2 with CATMAT support)
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
    -- V2 CATMAT columns
    catmat_codes TEXT[] DEFAULT '{}',
    has_medical_catmat BOOLEAN DEFAULT FALSE,
    catmat_score_boost INTEGER DEFAULT 0,
    sample_analyzed BOOLEAN DEFAULT FALSE,
    medical_confidence_score DECIMAL(5,2),
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
    price_comparison_brl DECIMAL(10,4), -- Homologated price in BRL
    price_comparison_usd DECIMAL(10,4), -- Converted price in USD
    exchange_rate DECIMAL(8,4), -- USD/BRL rate used
    price_difference_percent DECIMAL(6,2), -- % difference from FOB
    is_competitive BOOLEAN, -- Whether homologated price is competitive
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(tender_item_id, fernandes_product_code)
);

-- Processing log table
CREATE TABLE IF NOT EXISTS processing_log (
    id SERIAL PRIMARY KEY,
    process_type VARCHAR(50) NOT NULL, -- 'tender_discovery', 'item_extraction', 'price_analysis'
    state_code VARCHAR(2),
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,
    status VARCHAR(20) NOT NULL, -- 'running', 'completed', 'failed'
    records_processed INTEGER DEFAULT 0,
    records_matched INTEGER DEFAULT 0,
    error_message TEXT,
    metadata JSONB, -- Additional process metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Homologated results table (detailed results storage)
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
    additional_data JSONB, -- Store any additional result data
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(tender_item_id, result_sequential)
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_organizations_cnpj ON organizations(cnpj);
CREATE INDEX IF NOT EXISTS idx_organizations_state ON organizations(state_code);
CREATE INDEX IF NOT EXISTS idx_organizations_gov_level ON organizations(government_level);

CREATE INDEX IF NOT EXISTS idx_tenders_cnpj_ano_seq ON tenders(cnpj, ano, sequencial);
CREATE INDEX IF NOT EXISTS idx_tenders_control_number ON tenders(control_number);
CREATE INDEX IF NOT EXISTS idx_tenders_state ON tenders(state_code);
CREATE INDEX IF NOT EXISTS idx_tenders_gov_level ON tenders(government_level);
CREATE INDEX IF NOT EXISTS idx_tenders_publication_date ON tenders(publication_date);
CREATE INDEX IF NOT EXISTS idx_tenders_homologated_value ON tenders(total_homologated_value);

CREATE INDEX IF NOT EXISTS idx_tender_items_tender_id ON tender_items(tender_id);
CREATE INDEX IF NOT EXISTS idx_tender_items_item_number ON tender_items(item_number);
-- V2 CATMAT indexes
CREATE INDEX IF NOT EXISTS idx_tender_items_medical_catmat ON tender_items(has_medical_catmat) WHERE has_medical_catmat = TRUE;
CREATE INDEX IF NOT EXISTS idx_tender_items_catmat_codes ON tender_items USING GIN(catmat_codes);
CREATE INDEX IF NOT EXISTS idx_tender_items_medical_confidence ON tender_items(medical_confidence_score) WHERE medical_confidence_score >= 70.0;

CREATE INDEX IF NOT EXISTS idx_matched_products_tender_item_id ON matched_products(tender_item_id);
CREATE INDEX IF NOT EXISTS idx_matched_products_fernandes_code ON matched_products(fernandes_product_code);
CREATE INDEX IF NOT EXISTS idx_matched_products_match_score ON matched_products(match_score);

CREATE INDEX IF NOT EXISTS idx_processing_log_process_type ON processing_log(process_type);
CREATE INDEX IF NOT EXISTS idx_processing_log_state ON processing_log(state_code);
CREATE INDEX IF NOT EXISTS idx_processing_log_status ON processing_log(status);

CREATE INDEX IF NOT EXISTS idx_homologated_results_tender_item ON homologated_results(tender_item_id);
CREATE INDEX IF NOT EXISTS idx_homologated_results_winner ON homologated_results(is_winner);
"""

class DatabaseOperations:
    """Database operations for PNCP medical data"""

    def __init__(self, db_manager: CloudSQLManager):
        self.db_manager = db_manager

    async def initialize_database(self):
        """Create database schema"""
        try:
            conn = await self.db_manager.get_connection()
            async with conn.transaction():
                await conn.execute(DATABASE_SCHEMA)
            await conn.close()
            logger.info("Database schema initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise

    async def insert_organization(self, org_data: Dict[str, Any]) -> int:
        """Insert or update organization and return ID"""
        conn = await self.db_manager.get_connection()
        try:
            # Try to get existing organization
            existing = await conn.fetchrow(
                "SELECT id FROM organizations WHERE cnpj = $1",
                org_data['cnpj']
            )

            if existing:
                # Update existing
                await conn.execute("""
                    UPDATE organizations
                    SET name = $2, government_level = $3, organization_type = $4,
                        state_code = $5, municipality_name = $6, updated_at = CURRENT_TIMESTAMP
                    WHERE cnpj = $1
                """, org_data['cnpj'], org_data['name'], org_data['government_level'],
                    org_data.get('organization_type'), org_data.get('state_code'),
                    org_data.get('municipality_name'))
                return existing['id']
            else:
                # Insert new
                org_id = await conn.fetchval("""
                    INSERT INTO organizations (cnpj, name, government_level, organization_type, state_code, municipality_name)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    RETURNING id
                """, org_data['cnpj'], org_data['name'], org_data['government_level'],
                    org_data.get('organization_type'), org_data.get('state_code'),
                    org_data.get('municipality_name'))
                return org_id
        finally:
            await conn.close()

    async def insert_tender(self, tender_data: Dict[str, Any]) -> int:
        """Insert tender and return ID"""
        conn = await self.db_manager.get_connection()
        try:
            tender_id = await conn.fetchval("""
                INSERT INTO tenders (
                    organization_id, cnpj, ano, sequencial, control_number, title, description,
                    government_level, tender_size, contracting_modality, modality_name,
                    total_estimated_value, total_homologated_value, publication_date,
                    state_code, municipality_code, status, process_category
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18)
                ON CONFLICT (cnpj, ano, sequencial) DO UPDATE SET
                    total_homologated_value = EXCLUDED.total_homologated_value,
                    status = EXCLUDED.status,
                    updated_at = CURRENT_TIMESTAMP
                RETURNING id
            """, tender_data['organization_id'], tender_data['cnpj'], tender_data['ano'],
                tender_data['sequencial'], tender_data.get('control_number'),
                tender_data.get('title'), tender_data.get('description'),
                tender_data['government_level'], tender_data['tender_size'],
                tender_data.get('contracting_modality'), tender_data.get('modality_name'),
                tender_data.get('total_estimated_value'), tender_data.get('total_homologated_value'),
                tender_data.get('publication_date'), tender_data.get('state_code'),
                tender_data.get('municipality_code'), tender_data.get('status'),
                tender_data.get('process_category'))
            return tender_id
        finally:
            await conn.close()

    async def insert_tender_items_batch(self, items_data: List[Dict[str, Any]]):
        """Insert multiple tender items efficiently"""
        if not items_data:
            return

        conn = await self.db_manager.get_connection()
        try:
            await conn.executemany("""
                INSERT INTO tender_items (
                    tender_id, item_number, description, unit, quantity,
                    estimated_unit_value, estimated_total_value,
                    homologated_unit_value, homologated_total_value,
                    winner_name, winner_cnpj,
                    catmat_codes, has_medical_catmat, catmat_score_boost,
                    sample_analyzed, medical_confidence_score
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16)
                ON CONFLICT (tender_id, item_number) DO UPDATE SET
                    homologated_unit_value = EXCLUDED.homologated_unit_value,
                    homologated_total_value = EXCLUDED.homologated_total_value,
                    winner_name = EXCLUDED.winner_name,
                    winner_cnpj = EXCLUDED.winner_cnpj,
                    catmat_codes = EXCLUDED.catmat_codes,
                    has_medical_catmat = EXCLUDED.has_medical_catmat,
                    catmat_score_boost = EXCLUDED.catmat_score_boost,
                    sample_analyzed = EXCLUDED.sample_analyzed,
                    medical_confidence_score = EXCLUDED.medical_confidence_score,
                    updated_at = CURRENT_TIMESTAMP
            """, [
                (item['tender_id'], item['item_number'], item['description'],
                 item.get('unit'), item.get('quantity'),
                 item.get('estimated_unit_value'), item.get('estimated_total_value'),
                 item.get('homologated_unit_value'), item.get('homologated_total_value'),
                 item.get('winner_name'), item.get('winner_cnpj'),
                 item.get('catmat_codes') if item.get('catmat_codes') else [],
                 item.get('has_medical_catmat', False),
                 item.get('catmat_score_boost', 0), item.get('sample_analyzed', False),
                 item.get('medical_confidence_score'))
                for item in items_data
            ])
        finally:
            await conn.close()

    async def get_unprocessed_tenders(self, state_code: str = None, limit: int = 100) -> List[Dict]:
        """Get tenders that haven't been processed for item extraction"""
        conn = await self.db_manager.get_connection()
        try:
            query = """
                SELECT t.id, t.cnpj, t.ano, t.sequencial, t.government_level,
                       t.total_homologated_value, t.state_code
                FROM tenders t
                LEFT JOIN tender_items ti ON t.id = ti.tender_id
                WHERE t.total_homologated_value > 0
                  AND ti.tender_id IS NULL
            """
            params = []

            if state_code:
                query += " AND t.state_code = $1"
                params.append(state_code)
                query += " ORDER BY t.total_homologated_value DESC LIMIT $2"
            else:
                query += " ORDER BY t.total_homologated_value DESC LIMIT $1"

            params.append(limit)

            rows = await conn.fetch(query, *params)
            return [dict(row) for row in rows]
        finally:
            await conn.close()

    async def filter_new_tenders(self, fetched_tenders: List[Dict]) -> List[Dict]:
        """
        Filter out tenders that already exist in database by control number.
        Returns only NEW tenders that haven't been processed yet.

        This enables efficient deduplication across different states, dates, and modalities.
        """
        if not fetched_tenders:
            return []

        # Extract control numbers from fetched tenders
        control_numbers = []
        for t in fetched_tenders:
            control_num = t.get('numeroControlePNCP')
            if control_num:
                control_numbers.append(control_num)

        if not control_numbers:
            logger.warning("No control numbers found in fetched tenders")
            return fetched_tenders

        conn = await self.db_manager.get_connection()
        try:
            # Query database for existing tenders by control number
            query = """
                SELECT control_number
                FROM tenders
                WHERE control_number = ANY($1)
            """

            existing_rows = await conn.fetch(query, control_numbers)
            existing_set = {row['control_number'] for row in existing_rows}

            # Filter to only new tenders
            new_tenders = [
                t for t in fetched_tenders
                if t.get('numeroControlePNCP') not in existing_set
            ]

            duplicates_count = len(fetched_tenders) - len(new_tenders)

            logger.info(
                f"Tender deduplication: {len(fetched_tenders)} fetched → "
                f"{len(new_tenders)} new, {duplicates_count} already in DB "
                f"({duplicates_count/len(fetched_tenders)*100:.1f}% duplicates)"
            )

            return new_tenders

        finally:
            await conn.close()

    async def get_tender_items(self, tender_id: int, limit: int = None) -> List[Dict]:
        """Get items for a specific tender"""
        conn = await self.db_manager.get_connection()
        try:
            params = [tender_id]
            query = """
                SELECT *
                FROM tender_items
                WHERE tender_id = $1
                ORDER BY item_number
            """
            if limit:
                query += " LIMIT $2"
                params.append(limit)

            rows = await conn.fetch(query, *params)
            return [dict(row) for row in rows]
        finally:
            await conn.close()

    async def log_processing_start(self, process_type: str, state_code: str = None,
                                  metadata: Dict = None) -> int:
        """Log start of processing operation"""
        import json
        conn = await self.db_manager.get_connection()
        try:
            # Convert metadata dict to JSON string for JSONB column
            metadata_json = json.dumps(metadata) if metadata else None
            log_id = await conn.fetchval("""
                INSERT INTO processing_log (process_type, state_code, start_time, status, metadata)
                VALUES ($1, $2, CURRENT_TIMESTAMP, 'running', $3)
                RETURNING id
            """, process_type, state_code, metadata_json)
            return log_id
        finally:
            await conn.close()

    async def log_processing_end(self, log_id: int, status: str, records_processed: int = 0,
                               records_matched: int = 0, error_message: str = None):
        """Log end of processing operation"""
        conn = await self.db_manager.get_connection()
        try:
            await conn.execute("""
                UPDATE processing_log
                SET end_time = CURRENT_TIMESTAMP, status = $2, records_processed = $3,
                    records_matched = $4, error_message = $5
                WHERE id = $1
            """, log_id, status, records_processed, records_matched, error_message)
        finally:
            await conn.close()

# Utility function to create database manager from environment variables
def create_db_manager_from_env() -> CloudSQLManager:
    """Create database manager from environment variables"""
    project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
    region = os.getenv('CLOUD_SQL_REGION', 'us-central1')
    instance_name = os.getenv('CLOUD_SQL_INSTANCE')
    database_name = os.getenv('DATABASE_NAME', DatabaseConfig.DATABASE_NAME)

    if not all([project_id, instance_name]):
        raise ValueError("Missing required environment variables: GOOGLE_CLOUD_PROJECT, CLOUD_SQL_INSTANCE")

    return CloudSQLManager(project_id, region, instance_name, database_name)