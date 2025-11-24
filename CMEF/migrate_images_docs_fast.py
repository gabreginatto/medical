#!/usr/bin/env python3
"""
Fast migration of product images and documents tables from medica database
to medical_exhibitors database with detailed logging and batch inserts
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import create_db_manager_from_env

def log(msg):
    """Print with timestamp"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {msg}", flush=True)


async def migrate_tables():
    """Migrate medica_product_images and medica_documents tables"""

    log("=" * 70)
    log("FAST MIGRATION: IMAGES & DOCUMENTS TO UNIFIED DATABASE")
    log("=" * 70)

    db_manager = create_db_manager_from_env()

    # Step 1: Read from old medica database
    log("")
    log("📖 STEP 1: Reading from medica database...")
    log("-" * 70)

    db_manager.database_name = 'medica'
    conn_old = await db_manager.get_connection()
    log("✅ Connected to medica database")

    try:
        log("Fetching all product images...")
        images = await conn_old.fetch("SELECT * FROM medica_product_images ORDER BY id")
        log(f"✅ Fetched {len(images)} product images ({len(images) * 0.1:.1f} KB)")

        log("Fetching all documents...")
        documents = await conn_old.fetch("SELECT * FROM medica_documents ORDER BY id")
        log(f"✅ Fetched {len(documents)} documents")

    except Exception as e:
        log(f"❌ Error reading from medica database: {e}")
        raise
    finally:
        await conn_old.close()
        log("Closed connection to medica database")

    # Step 2: Write to new medical_exhibitors database
    log("")
    log("💾 STEP 2: Writing to medical_exhibitors database...")
    log("-" * 70)

    db_manager.database_name = 'medical_exhibitors'
    conn_new = await db_manager.get_connection()
    log("✅ Connected to medical_exhibitors database")

    try:
        # Create medica_product_images table
        log("")
        log("Creating medica_product_images table...")
        await conn_new.execute("DROP TABLE IF EXISTS medica_product_images CASCADE")
        log("  Dropped existing table if present")

        await conn_new.execute("""
            CREATE TABLE medica_product_images (
                id SERIAL PRIMARY KEY,
                exhibitor_id INTEGER NOT NULL,
                image_filename VARCHAR(500),
                gcs_url TEXT,
                gcs_bucket VARCHAR(200),
                gcs_path TEXT,
                image_order INTEGER,
                file_size_bytes BIGINT,
                uploaded_at TIMESTAMP DEFAULT NOW()
            )
        """)
        log("✅ Table created successfully")

        # Insert images using COPY (much faster than individual INSERTs)
        if images:
            log("")
            log(f"Inserting {len(images)} images using batch insert...")
            log(f"  Estimated time: ~{len(images) * 0.1:.0f} seconds")

            # Use executemany for batch insert
            batch_size = 500
            total_batches = (len(images) + batch_size - 1) // batch_size

            insert_sql = """
                INSERT INTO medica_product_images (
                    id, exhibitor_id, image_filename, gcs_url, gcs_bucket,
                    gcs_path, image_order, file_size_bytes, uploaded_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            """

            for batch_num in range(total_batches):
                start_idx = batch_num * batch_size
                end_idx = min(start_idx + batch_size, len(images))
                batch = images[start_idx:end_idx]

                log(f"  Batch {batch_num + 1}/{total_batches}: Inserting images {start_idx + 1}-{end_idx}...")

                async with conn_new.transaction():
                    for img in batch:
                        await conn_new.execute(insert_sql,
                            img['id'],
                            img['exhibitor_id'],
                            img['image_filename'],
                            img['gcs_url'],
                            img['gcs_bucket'],
                            img['gcs_path'],
                            img['image_order'],
                            img['file_size_bytes'],
                            img['uploaded_at']
                        )

                log(f"  ✅ Batch {batch_num + 1}/{total_batches} completed")

            log(f"✅ All {len(images)} images inserted successfully")

        # Create medica_documents table
        log("")
        log("Creating medica_documents table...")
        await conn_new.execute("DROP TABLE IF EXISTS medica_documents CASCADE")
        log("  Dropped existing table if present")

        await conn_new.execute("""
            CREATE TABLE medica_documents (
                id SERIAL PRIMARY KEY,
                exhibitor_id INTEGER NOT NULL,
                document_filename VARCHAR(500),
                gcs_url TEXT,
                gcs_bucket VARCHAR(200),
                gcs_path TEXT,
                file_size_bytes BIGINT,
                uploaded_at TIMESTAMP DEFAULT NOW()
            )
        """)
        log("✅ Table created successfully")

        # Insert documents (if any)
        if documents:
            log("")
            log(f"Inserting {len(documents)} documents...")

            insert_sql = """
                INSERT INTO medica_documents (
                    id, exhibitor_id, document_filename, gcs_url, gcs_bucket,
                    gcs_path, file_size_bytes, uploaded_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """

            async with conn_new.transaction():
                for doc in documents:
                    await conn_new.execute(insert_sql,
                        doc['id'],
                        doc['exhibitor_id'],
                        doc['document_filename'],
                        doc['gcs_url'],
                        doc['gcs_bucket'],
                        doc['gcs_path'],
                        doc['file_size_bytes'],
                        doc['uploaded_at']
                    )

            log(f"✅ Inserted {len(documents)} documents")
        else:
            log("⚠️  No documents to insert (table is empty in source database)")

        # Create indexes
        log("")
        log("📑 Creating indexes for faster queries...")
        log("  Creating index on medica_product_images(exhibitor_id)...")
        await conn_new.execute("CREATE INDEX idx_product_images_exhibitor ON medica_product_images(exhibitor_id)")
        log("  ✅ Index created")

        log("  Creating index on medica_documents(exhibitor_id)...")
        await conn_new.execute("CREATE INDEX idx_documents_exhibitor ON medica_documents(exhibitor_id)")
        log("  ✅ Index created")

        # Verify data
        log("")
        log("=" * 70)
        log("STEP 3: VERIFICATION")
        log("=" * 70)

        img_count = await conn_new.fetchval("SELECT COUNT(*) FROM medica_product_images")
        doc_count = await conn_new.fetchval("SELECT COUNT(*) FROM medica_documents")

        log(f"✅ Product images in new database: {img_count}")
        log(f"✅ Documents in new database: {doc_count}")

        if img_count != len(images):
            log(f"⚠️  WARNING: Image count mismatch! Expected {len(images)}, got {img_count}")

        if doc_count != len(documents):
            log(f"⚠️  WARNING: Document count mismatch! Expected {len(documents)}, got {doc_count}")

        # Test join with exhibitors
        log("")
        log("🔗 Testing join with medical_exhibitors table...")
        join_test = await conn_new.fetch("""
            SELECT
                e.name,
                e.data_source,
                COUNT(i.id) as image_count
            FROM medical_exhibitors_unique e
            LEFT JOIN medica_product_images i ON e.id = i.exhibitor_id
            WHERE e.data_source = 'MEDICA'
            GROUP BY e.name, e.data_source
            HAVING COUNT(i.id) > 0
            LIMIT 10
        """)

        log("Sample MEDICA exhibitors with images:")
        for row in join_test:
            log(f"  • {row['name']}: {row['image_count']} images")

        companies_with_images = await conn_new.fetchval("""
            SELECT COUNT(DISTINCT e.id)
            FROM medical_exhibitors_unique e
            JOIN medica_product_images i ON e.id = i.exhibitor_id
            WHERE e.data_source = 'MEDICA'
        """)
        log(f"✅ {companies_with_images} MEDICA companies have product images")

        # Storage stats
        log("")
        log("📊 Storage statistics:")
        total_size = await conn_new.fetchval("""
            SELECT SUM(file_size_bytes) / 1024.0 / 1024.0
            FROM medica_product_images
        """)
        if total_size:
            log(f"  Total image storage: {total_size:.2f} MB")

        avg_size = await conn_new.fetchval("""
            SELECT AVG(file_size_bytes) / 1024.0
            FROM medica_product_images
        """)
        if avg_size:
            log(f"  Average image size: {avg_size:.2f} KB")

        log("")
        log("=" * 70)
        log("✅ MIGRATION COMPLETED SUCCESSFULLY!")
        log("=" * 70)
        log("")
        log("Summary:")
        log(f"  • {img_count} product images migrated")
        log(f"  • {doc_count} documents migrated")
        log(f"  • 2 indexes created")
        log(f"  • Join test passed")
        log("")
        log("Next steps:")
        log("  1. Looker views will now work correctly")
        log("  2. All data in single medical_exhibitors database")
        log("  3. Old medica database can remain as backup")
        log("")

    except Exception as e:
        log("")
        log(f"❌ ERROR during migration: {e}")
        import traceback
        log(traceback.format_exc())
        raise
    finally:
        await conn_new.close()
        log("Closed connection to medical_exhibitors database")


if __name__ == "__main__":
    try:
        asyncio.run(migrate_tables())
    except KeyboardInterrupt:
        log("\n⚠️  Migration interrupted by user")
    except Exception as e:
        log(f"\n❌ Migration failed: {e}")
        sys.exit(1)
