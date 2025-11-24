#!/usr/bin/env python3
"""
Setup Unified Medical Exhibitors Database

Creates new database and imports both CMEF and MEDICA enriched data.
"""

import json
import logging
import asyncpg
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/unified_db_setup.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class UnifiedDatabaseSetup:
    """Setup unified database with CMEF and MEDICA data"""

    def __init__(self, db_url: str):
        self.db_url = db_url

    async def create_schema(self):
        """Create the unified schema"""

        logger.info("=" * 70)
        logger.info("CREATING UNIFIED DATABASE SCHEMA")
        logger.info("=" * 70)

        conn = await asyncpg.connect(self.db_url)

        try:
            # Create main table
            logger.info("\n📊 Creating medical_exhibitors table...")

            await conn.execute("""
                CREATE TABLE IF NOT EXISTS medical_exhibitors (
                    -- Primary Key
                    id SERIAL PRIMARY KEY,

                    -- Basic Company Information
                    name VARCHAR(500) NOT NULL,
                    company_name_zh VARCHAR(500),
                    location VARCHAR(200),
                    booth_number VARCHAR(50),

                    -- Contact Information
                    email VARCHAR(255),
                    phone VARCHAR(100),
                    website VARCHAR(500),
                    address TEXT,
                    country VARCHAR(100),
                    region VARCHAR(50),

                    -- Event Tracking
                    event VARCHAR(100) NOT NULL,
                    data_source VARCHAR(50) NOT NULL,

                    -- Company Description
                    company_description TEXT,
                    raw_text TEXT,

                    -- AI Product Classification
                    product_category VARCHAR(200),
                    product_keywords TEXT[],
                    category_confidence FLOAT,

                    -- Website Validation
                    website_validated BOOLEAN DEFAULT FALSE,
                    website_status_code INTEGER,

                    -- Timestamps
                    scraped_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW(),

                    -- Constraints
                    CONSTRAINT unique_company_event UNIQUE(name, event)
                )
            """)

            logger.info("✅ Table created")

            # Create indexes
            logger.info("\n📑 Creating indexes...")

            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_exhibitors_name ON medical_exhibitors(name)",
                "CREATE INDEX IF NOT EXISTS idx_exhibitors_country ON medical_exhibitors(country)",
                "CREATE INDEX IF NOT EXISTS idx_exhibitors_event ON medical_exhibitors(event)",
                "CREATE INDEX IF NOT EXISTS idx_exhibitors_data_source ON medical_exhibitors(data_source)",
                "CREATE INDEX IF NOT EXISTS idx_exhibitors_category ON medical_exhibitors(product_category)",
                "CREATE INDEX IF NOT EXISTS idx_exhibitors_booth ON medical_exhibitors(booth_number)",
                "CREATE INDEX IF NOT EXISTS idx_exhibitors_keywords ON medical_exhibitors USING GIN(product_keywords)",
                "CREATE INDEX IF NOT EXISTS idx_exhibitors_description ON medical_exhibitors USING GIN(to_tsvector('english', company_description))",
            ]

            for idx_sql in indexes:
                await conn.execute(idx_sql)

            logger.info(f"✅ Created {len(indexes)} indexes")

            # Create trigger for updated_at
            logger.info("\n⚙️  Creating triggers...")

            await conn.execute("""
                CREATE OR REPLACE FUNCTION update_updated_at_column()
                RETURNS TRIGGER AS $$
                BEGIN
                    NEW.updated_at = NOW();
                    RETURN NEW;
                END;
                $$ LANGUAGE plpgsql
            """)

            await conn.execute("""
                DROP TRIGGER IF EXISTS update_medical_exhibitors_updated_at ON medical_exhibitors
            """)

            await conn.execute("""
                CREATE TRIGGER update_medical_exhibitors_updated_at
                    BEFORE UPDATE ON medical_exhibitors
                    FOR EACH ROW
                    EXECUTE FUNCTION update_updated_at_column()
            """)

            logger.info("✅ Triggers created")

        finally:
            await conn.close()

    async def import_cmef_data(self, cmef_json_path: str):
        """Import CMEF enriched data"""

        logger.info("\n" + "=" * 70)
        logger.info("IMPORTING CMEF DATA")
        logger.info("=" * 70)

        # Load CMEF data
        with open(cmef_json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        companies = data.get('companies', [])
        logger.info(f"📖 Loaded {len(companies)} CMEF companies")

        conn = await asyncpg.connect(self.db_url)

        try:
            insert_sql = """
                INSERT INTO medical_exhibitors (
                    name, company_name_zh, location, booth_number,
                    company_description, email, phone, website, address,
                    country, region, event,
                    product_category, product_keywords, category_confidence,
                    website_validated, website_status_code,
                    data_source, scraped_at
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, NOW()
                )
            """

            async with conn.transaction():
                for i, company in enumerate(companies, 1):
                    await conn.execute(insert_sql,
                        company.get('company_name_en'),
                        company.get('company_name_zh'),
                        company.get('booth_number'),
                        company.get('booth_number'),
                        company.get('scope_description'),
                        company.get('email'),
                        company.get('phone'),
                        company.get('website'),
                        company.get('address'),
                        'China',
                        'China',
                        'CMEF 2025',
                        company.get('product_category'),
                        company.get('product_keywords', []),
                        company.get('category_confidence'),
                        company.get('website_validated', False),
                        company.get('website_status_code'),
                        'CMEF'
                    )

                    if i % 100 == 0:
                        logger.info(f"  Imported {i}/{len(companies)} companies")

            logger.info(f"✅ Imported {len(companies)} CMEF companies")

        finally:
            await conn.close()

    async def import_medica_data(self, medica_json_path: str):
        """Import MEDICA enriched data"""

        logger.info("\n" + "=" * 70)
        logger.info("IMPORTING MEDICA DATA")
        logger.info("=" * 70)

        # Load MEDICA data
        with open(medica_json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        companies = data.get('exhibitors', [])
        logger.info(f"📖 Loaded {len(companies)} MEDICA companies")

        conn = await asyncpg.connect(self.db_url)

        try:
            insert_sql = """
                INSERT INTO medical_exhibitors (
                    name, location, company_description,
                    email, phone, website, address, raw_text,
                    country, region, event,
                    product_category, product_keywords, category_confidence,
                    data_source, scraped_at
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, NOW()
                )
            """

            async with conn.transaction():
                for i, company in enumerate(companies, 1):
                    await conn.execute(insert_sql,
                        company.get('name'),
                        company.get('location'),
                        company.get('company_description'),
                        company.get('email'),
                        company.get('phone'),
                        company.get('website'),
                        company.get('address'),
                        company.get('raw_text'),
                        company.get('country'),
                        company.get('region'),
                        'MEDICA 2025',
                        company.get('product_category'),
                        company.get('product_keywords', []),
                        company.get('category_confidence'),
                        'MEDICA'
                    )

                    if i % 100 == 0:
                        logger.info(f"  Imported {i}/{len(companies)} companies")

            logger.info(f"✅ Imported {len(companies)} MEDICA companies")

        finally:
            await conn.close()

    async def print_summary(self):
        """Print database summary"""

        logger.info("\n" + "=" * 70)
        logger.info("UNIFIED DATABASE SUMMARY")
        logger.info("=" * 70)

        conn = await asyncpg.connect(self.db_url)

        try:
            # Total by source
            rows = await conn.fetch("""
                SELECT
                    data_source,
                    COUNT(*) as total,
                    COUNT(product_category) as classified,
                    AVG(category_confidence) as avg_confidence
                FROM medical_exhibitors
                GROUP BY data_source
                ORDER BY data_source
            """)

            logger.info("\n📊 By Data Source:")
            total_all = 0
            for row in rows:
                total_all += row['total']
                logger.info(f"  {row['data_source']}: {row['total']} companies")
                logger.info(f"    Classified: {row['classified']} ({row['classified']/row['total']*100:.1f}%)")
                logger.info(f"    Avg Confidence: {row['avg_confidence']:.2f if row['avg_confidence'] else 0}")

            logger.info(f"\n📈 TOTAL: {total_all} companies")

            # Top categories
            rows = await conn.fetch("""
                SELECT
                    product_category,
                    COUNT(*) FILTER (WHERE data_source = 'MEDICA') as medica_count,
                    COUNT(*) FILTER (WHERE data_source = 'CMEF') as cmef_count,
                    COUNT(*) as total_count
                FROM medical_exhibitors
                WHERE product_category IS NOT NULL
                GROUP BY product_category
                ORDER BY total_count DESC
                LIMIT 10
            """)

            logger.info("\n📂 Top 10 Categories (Unified):")
            for row in rows:
                logger.info(f"  {row['product_category']}: {row['total_count']} "
                           f"(MEDICA: {row['medica_count']}, CMEF: {row['cmef_count']})")

        finally:
            await conn.close()


async def main():
    """Main entry point"""

    logger.info("=" * 70)
    logger.info("UNIFIED MEDICAL EXHIBITORS DATABASE SETUP")
    logger.info("=" * 70)
    logger.info(f"Started: {datetime.now().isoformat()}")
    logger.info("")

    # Database URL
    db_url = input("Enter database URL (e.g., postgresql://user:pass@host:5432/medical_exhibitors):\n> ").strip()

    # File paths
    cmef_json = '/Users/gabrielreginatto/Desktop/Code/Medical/CMEF/data/enriched_companies.json'
    medica_json = '/Users/gabrielreginatto/Desktop/Code/Medical/Medica/china_exhibitors_enriched.json'

    print("\n" + "=" * 70)
    print("SETUP PLAN")
    print("=" * 70)
    print(f"Database: {db_url.split('@')[1] if '@' in db_url else db_url}")
    print(f"\nCMEF data:   {cmef_json}")
    print(f"MEDICA data: {medica_json}")
    print("\nThis will:")
    print("  1. Create unified schema with indexes")
    print("  2. Import ~4,497 CMEF companies")
    print("  3. Import ~1,321 MEDICA companies")
    print("  4. Total: ~5,818 companies")
    print("=" * 70)

    confirm = input("\nProceed? (yes/no): ").strip().lower()
    if confirm != 'yes':
        logger.info("❌ Setup cancelled")
        return

    # Setup database
    setup = UnifiedDatabaseSetup(db_url)

    try:
        # Step 1: Create schema
        await setup.create_schema()

        # Step 2: Import CMEF
        await setup.import_cmef_data(cmef_json)

        # Step 3: Import MEDICA
        await setup.import_medica_data(medica_json)

        # Step 4: Summary
        await setup.print_summary()

        logger.info("\n" + "=" * 70)
        logger.info("✅ SETUP COMPLETED SUCCESSFULLY!")
        logger.info("=" * 70)
        logger.info("\nNext steps:")
        logger.info("  1. Update Looker connection to new database")
        logger.info("  2. Create dashboards with data_source filter")
        logger.info("  3. Test keyword search functionality")

    except Exception as e:
        logger.error(f"\n❌ Setup failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
