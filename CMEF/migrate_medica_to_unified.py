#!/usr/bin/env python3
"""
Migrate MEDICA Data to Unified Database

Safely copies existing MEDICA exhibitor data from the old 'medical' database
to the new 'medical_unified' database. Does NOT modify the original database.
"""

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import CloudSQLManager
import asyncpg

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/medica_migration.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class MedicaMigrator:
    """Migrate MEDICA data to unified database"""

    def __init__(self, source_db_url: str, target_db_url: str):
        """
        Args:
            source_db_url: Connection string for old medical database (read-only)
            target_db_url: Connection string for new medical_unified database
        """
        self.source_db_url = source_db_url
        self.target_db_url = target_db_url

    async def migrate(self):
        """Copy MEDICA data from old database to new unified database"""

        logger.info("=" * 70)
        logger.info("MEDICA DATA MIGRATION TO UNIFIED DATABASE")
        logger.info("=" * 70)
        logger.info(f"Source: {self.source_db_url.split('@')[1] if '@' in self.source_db_url else 'medical database'}")
        logger.info(f"Target: {self.target_db_url.split('@')[1] if '@' in self.target_db_url else 'medical_unified database'}")
        logger.info("=" * 70)

        # Connect to both databases
        logger.info("\n📡 Connecting to databases...")
        source_conn = await asyncpg.connect(self.source_db_url)
        target_conn = await asyncpg.connect(self.target_db_url)

        try:
            # Get MEDICA data from old database (READ ONLY)
            logger.info("\n📖 Reading MEDICA data from source database...")
            rows = await source_conn.fetch("""
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
                    updated_at
                FROM medica_exhibitors
                ORDER BY id
            """)

            companies = [dict(row) for row in rows]
            logger.info(f"✅ Found {len(companies)} MEDICA companies to migrate")

            if not companies:
                logger.warning("⚠️  No MEDICA companies found in source database!")
                return

            # Show sample company
            logger.info(f"\n📋 Sample company: {companies[0]['name']}")

            # Insert into new unified database
            logger.info(f"\n💾 Inserting {len(companies)} companies into unified database...")

            insert_sql = """
            INSERT INTO medical_exhibitors (
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
                data_source,
                scraped_at,
                created_at,
                updated_at
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15
            )
            ON CONFLICT (name, event) DO UPDATE SET
                location = EXCLUDED.location,
                company_description = EXCLUDED.company_description,
                email = EXCLUDED.email,
                phone = EXCLUDED.phone,
                website = EXCLUDED.website,
                address = EXCLUDED.address,
                raw_text = EXCLUDED.raw_text,
                country = EXCLUDED.country,
                region = EXCLUDED.region,
                updated_at = NOW()
            """

            async with target_conn.transaction():
                for i, company in enumerate(companies, 1):
                    await target_conn.execute(insert_sql,
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
                        company.get('event', 'MEDICA 2025'),
                        'MEDICA',  # data_source
                        company.get('scraped_at'),
                        company.get('created_at'),
                        company.get('updated_at')
                    )

                    if i % 100 == 0:
                        logger.info(f"  Migrated {i}/{len(companies)} companies")

            logger.info(f"\n✅ Successfully migrated {len(companies)} MEDICA companies")

            # Verify migration
            await self._verify_migration(source_conn, target_conn)

            # Print summary
            await self._print_summary(target_conn)

        except Exception as e:
            logger.error(f"❌ Migration error: {e}")
            raise
        finally:
            await source_conn.close()
            await target_conn.close()

    async def _verify_migration(self, source_conn, target_conn):
        """Verify data was migrated correctly"""
        logger.info("\n🔍 Verifying migration...")

        # Count in source
        source_count = await source_conn.fetchval(
            "SELECT COUNT(*) FROM medica_exhibitors"
        )

        # Count in target
        target_count = await target_conn.fetchval(
            "SELECT COUNT(*) FROM medical_exhibitors WHERE data_source = 'MEDICA'"
        )

        logger.info(f"  Source database: {source_count} companies")
        logger.info(f"  Target database: {target_count} MEDICA companies")

        if source_count == target_count:
            logger.info("  ✅ Counts match - migration successful!")
        else:
            logger.warning(f"  ⚠️  Count mismatch! Missing {source_count - target_count} companies")

        # Sample verification
        sample = await source_conn.fetchrow(
            "SELECT name, website FROM medica_exhibitors ORDER BY id LIMIT 1"
        )
        if sample:
            target_sample = await target_conn.fetchrow(
                "SELECT name, website FROM medical_exhibitors WHERE name = $1 AND data_source = 'MEDICA'",
                sample['name']
            )
            if target_sample and target_sample['website'] == sample['website']:
                logger.info(f"  ✅ Sample record verified: {sample['name']}")
            else:
                logger.warning(f"  ⚠️  Sample record mismatch for {sample['name']}")

    async def _print_summary(self, conn):
        """Print migration statistics"""
        logger.info("\n" + "=" * 70)
        logger.info("UNIFIED DATABASE SUMMARY")
        logger.info("=" * 70)

        # Total by source
        rows = await conn.fetch("""
            SELECT
                data_source,
                COUNT(*) as total,
                COUNT(product_category) as classified
            FROM medical_exhibitors
            GROUP BY data_source
            ORDER BY data_source
        """)

        logger.info("\nBy Data Source:")
        for row in rows:
            logger.info(f"  {row['data_source']}: {row['total']} companies "
                       f"({row['classified']} classified)")

        # Total by event
        rows = await conn.fetch("""
            SELECT event, data_source, COUNT(*) as count
            FROM medical_exhibitors
            GROUP BY event, data_source
            ORDER BY data_source, event
        """)

        logger.info("\nBy Event:")
        for row in rows:
            logger.info(f"  {row['event']} ({row['data_source']}): {row['count']}")

        # Countries
        rows = await conn.fetch("""
            SELECT country, COUNT(*) as count
            FROM medical_exhibitors
            WHERE data_source = 'MEDICA'
            GROUP BY country
            ORDER BY count DESC
            LIMIT 10
        """)

        logger.info("\nTop 10 Countries (MEDICA):")
        for row in rows:
            logger.info(f"  {row['country']}: {row['count']}")


async def main():
    """Main entry point"""
    import os

    logger.info("Starting MEDICA data migration to unified database...")

    # Database connection strings
    # Source: OLD medical database (read-only)
    source_db = os.getenv('SOURCE_DB_URL') or input(
        "Enter SOURCE database URL (old 'medical' database):\n"
        "Format: postgresql://user:password@host:5432/medical\n> "
    )

    # Target: NEW medical_unified database
    target_db = os.getenv('TARGET_DB_URL') or input(
        "\nEnter TARGET database URL (new 'medical_unified' database):\n"
        "Format: postgresql://user:password@host:5432/medical_unified\n> "
    )

    # Confirm before proceeding
    print("\n" + "=" * 70)
    print("MIGRATION PLAN")
    print("=" * 70)
    print(f"📖 READ from: {source_db.split('@')[1] if '@' in source_db else source_db}")
    print(f"💾 WRITE to: {target_db.split('@')[1] if '@' in target_db else target_db}")
    print("\nThis operation will:")
    print("  1. READ all data from source database (no modifications)")
    print("  2. COPY data to target database (safe operation)")
    print("  3. Set data_source = 'MEDICA' for all records")
    print("=" * 70)

    confirm = input("\nProceed with migration? (yes/no): ").strip().lower()
    if confirm != 'yes':
        logger.info("❌ Migration cancelled by user")
        return

    # Run migration
    migrator = MedicaMigrator(source_db, target_db)
    await migrator.migrate()

    logger.info("\n✅ MEDICA migration completed successfully!")
    logger.info("\n🎉 Unified database ready for CMEF import!")
    logger.info("\nNext steps:")
    logger.info("  1. Run: python3 import_cmef_to_unified.py (import CMEF companies)")
    logger.info("  2. Run: python3 classify_unified_companies.py (classify all companies)")
    logger.info("  3. Update Looker connection to point to new database")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
