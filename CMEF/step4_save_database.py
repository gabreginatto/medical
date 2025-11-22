#!/usr/bin/env python3
"""
Step 4: Save to Database

Saves enriched company data to PostgreSQL database.
"""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path to import src modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import get_db_connection
from config import CMEFConfig, DEFAULT_CONFIG

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/database.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class DatabaseSaver:
    """Saves CMEF data to PostgreSQL"""

    def __init__(self, config: CMEFConfig = DEFAULT_CONFIG):
        self.config = config

    def create_table(self, conn):
        """Create cmef_companies table if not exists"""
        logger.info("Creating table schema...")

        create_table_sql = f"""
        CREATE TABLE IF NOT EXISTS {self.config.DATABASE_TABLE} (
            id SERIAL PRIMARY KEY,

            -- Company Information (from OCR)
            company_name_en VARCHAR(500),
            company_name_zh VARCHAR(500),
            booth_number VARCHAR(50),
            address TEXT,
            email VARCHAR(255),
            website VARCHAR(500),
            phone VARCHAR(100),
            scope_description TEXT,

            -- Product Classification (from Gemini)
            product_category VARCHAR(200),
            product_keywords TEXT[],
            category_confidence FLOAT,

            -- Regulatory Classifications (to be enriched later)
            ncm_code VARCHAR(20),
            anvisa_risk_class VARCHAR(10),

            -- Validation
            website_validated BOOLEAN,
            website_status_code INTEGER,

            -- Metadata
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        );

        -- Indexes for searching
        CREATE INDEX IF NOT EXISTS idx_cmef_category ON {self.config.DATABASE_TABLE}(product_category);
        CREATE INDEX IF NOT EXISTS idx_cmef_company_name ON {self.config.DATABASE_TABLE}(company_name_en);
        CREATE INDEX IF NOT EXISTS idx_cmef_booth ON {self.config.DATABASE_TABLE}(booth_number);
        CREATE INDEX IF NOT EXISTS idx_cmef_ncm ON {self.config.DATABASE_TABLE}(ncm_code);
        CREATE INDEX IF NOT EXISTS idx_cmef_anvisa ON {self.config.DATABASE_TABLE}(anvisa_risk_class);

        -- GIN index for keyword array searching
        CREATE INDEX IF NOT EXISTS idx_cmef_keywords ON {self.config.DATABASE_TABLE} USING GIN(product_keywords);
        """

        with conn.cursor() as cur:
            cur.execute(create_table_sql)
        conn.commit()

        logger.info(f"✅ Table '{self.config.DATABASE_TABLE}' ready")

    def save_companies(self, input_file: str = None):
        """Save companies to database"""
        input_file = input_file or self.config.get_full_path(self.config.ENRICHED_OUTPUT_FILE)

        logger.info("=" * 70)
        logger.info("STEP 4: SAVE TO DATABASE")
        logger.info("=" * 70)

        # Load enriched data
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        companies = data.get('companies', [])
        logger.info(f"Loaded {len(companies)} companies")

        # Connect to database
        logger.info("\nConnecting to database...")
        conn = get_db_connection()

        try:
            # Create table
            self.create_table(conn)

            # Insert companies
            logger.info(f"\nInserting {len(companies)} companies...")

            insert_sql = f"""
            INSERT INTO {self.config.DATABASE_TABLE} (
                company_name_en, company_name_zh, booth_number, address, email, website, phone,
                scope_description, product_category, product_keywords, category_confidence,
                ncm_code, anvisa_risk_class, website_validated, website_status_code
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            """

            with conn.cursor() as cur:
                for i, company in enumerate(companies, 1):
                    cur.execute(insert_sql, (
                        company.get('company_name_en'),
                        company.get('company_name_zh'),
                        company.get('booth_number'),
                        company.get('address'),
                        company.get('email'),
                        company.get('website'),
                        company.get('phone'),
                        company.get('scope_description'),
                        company.get('product_category'),
                        company.get('product_keywords', []),
                        company.get('category_confidence'),
                        company.get('ncm_code'),
                        company.get('anvisa_risk_class'),
                        company.get('website_validated'),
                        company.get('website_status_code')
                    ))

                    if i % 100 == 0:
                        logger.info(f"Inserted {i}/{len(companies)} companies")

            conn.commit()

            logger.info(f"\n✅ Successfully saved {len(companies)} companies to database")

            # Print summary
            self._print_database_summary(conn)

        except Exception as e:
            conn.rollback()
            logger.error(f"❌ Database error: {e}")
            raise
        finally:
            conn.close()

    def _print_database_summary(self, conn):
        """Print database statistics"""
        logger.info("\n" + "=" * 70)
        logger.info("DATABASE SUMMARY")
        logger.info("=" * 70)

        with conn.cursor() as cur:
            # Total count
            cur.execute(f"SELECT COUNT(*) FROM {self.config.DATABASE_TABLE}")
            total = cur.fetchone()[0]
            logger.info(f"Total companies: {total}")

            # By ANVISA risk class (will be null until enrichment)
            cur.execute(f"""
                SELECT anvisa_risk_class, COUNT(*)
                FROM {self.config.DATABASE_TABLE}
                GROUP BY anvisa_risk_class
                ORDER BY anvisa_risk_class NULLS LAST
            """)
            logger.info("\nBy ANVISA Risk Class:")
            for risk_class, count in cur.fetchall():
                label = risk_class if risk_class else "Not classified yet"
                logger.info(f"  {label}: {count}")

            # By category (top 10)
            cur.execute(f"""
                SELECT product_category, COUNT(*) as count
                FROM {self.config.DATABASE_TABLE}
                GROUP BY product_category
                ORDER BY count DESC
                LIMIT 10
            """)
            logger.info("\nTop 10 Categories:")
            for category, count in cur.fetchall():
                logger.info(f"  {category}: {count}")


def main():
    saver = DatabaseSaver()

    try:
        saver.save_companies()
        logger.info("\n✅ Database save completed successfully!")
        logger.info("\n🎉 CMEF catalog processing pipeline complete!")
    except Exception as e:
        logger.error(f"\n❌ Error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise


if __name__ == "__main__":
    main()
