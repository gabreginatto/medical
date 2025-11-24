#!/usr/bin/env python3
"""
Migrate product images and documents tables from medica database
to medical_exhibitors database
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import create_db_manager_from_env

async def migrate_tables():
    """Migrate medica_product_images and medica_documents tables"""

    print("=" * 70)
    print("MIGRATING IMAGES & DOCUMENTS TO UNIFIED DATABASE")
    print("=" * 70)
    print()

    db_manager = create_db_manager_from_env()

    # Step 1: Read from old medica database
    print("📖 Step 1: Reading from medica database...")
    db_manager.database_name = 'medica'
    conn_old = await db_manager.get_connection()

    try:
        # Get all product images
        images = await conn_old.fetch("SELECT * FROM medica_product_images ORDER BY id")
        print(f"✅ Found {len(images)} product images")

        # Get all documents
        documents = await conn_old.fetch("SELECT * FROM medica_documents ORDER BY id")
        print(f"✅ Found {len(documents)} documents")

    finally:
        await conn_old.close()

    # Step 2: Write to new medical_exhibitors database
    print()
    print("💾 Step 2: Writing to medical_exhibitors database...")
    db_manager.database_name = 'medical_exhibitors'
    conn_new = await db_manager.get_connection()

    try:
        # Create medica_product_images table
        print("Creating medica_product_images table...")
        await conn_new.execute("DROP TABLE IF EXISTS medica_product_images CASCADE")
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
        print("✅ Table created")

        # Insert images
        if images:
            print(f"Inserting {len(images)} images...")
            async with conn_new.transaction():
                for img in images:
                    await conn_new.execute("""
                        INSERT INTO medica_product_images (
                            id, exhibitor_id, image_filename, gcs_url, gcs_bucket,
                            gcs_path, image_order, file_size_bytes, uploaded_at
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    """,
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
            print(f"✅ Inserted {len(images)} images")

        # Create medica_documents table
        print()
        print("Creating medica_documents table...")
        await conn_new.execute("DROP TABLE IF EXISTS medica_documents CASCADE")
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
        print("✅ Table created")

        # Insert documents (if any)
        if documents:
            print(f"Inserting {len(documents)} documents...")
            async with conn_new.transaction():
                for doc in documents:
                    await conn_new.execute("""
                        INSERT INTO medica_documents (
                            id, exhibitor_id, document_filename, gcs_url, gcs_bucket,
                            gcs_path, file_size_bytes, uploaded_at
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    """,
                        doc['id'],
                        doc['exhibitor_id'],
                        doc['document_filename'],
                        doc['gcs_url'],
                        doc['gcs_bucket'],
                        doc['gcs_path'],
                        doc['file_size_bytes'],
                        doc['uploaded_at']
                    )
            print(f"✅ Inserted {len(documents)} documents")
        else:
            print("⚠️  No documents to insert (table is empty)")

        # Create indexes
        print()
        print("📑 Creating indexes...")
        await conn_new.execute("CREATE INDEX idx_product_images_exhibitor ON medica_product_images(exhibitor_id)")
        await conn_new.execute("CREATE INDEX idx_documents_exhibitor ON medica_documents(exhibitor_id)")
        print("✅ Indexes created")

        # Verify data
        print()
        print("=" * 70)
        print("VERIFICATION")
        print("=" * 70)

        img_count = await conn_new.fetchval("SELECT COUNT(*) FROM medica_product_images")
        doc_count = await conn_new.fetchval("SELECT COUNT(*) FROM medica_documents")

        print(f"✅ Product images in new database: {img_count}")
        print(f"✅ Documents in new database: {doc_count}")

        # Test join with exhibitors
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
            LIMIT 5
        """)

        print()
        print("🔗 Sample join test (MEDICA exhibitors with images):")
        for row in join_test:
            print(f"  {row['name']}: {row['image_count']} images")

        print()
        print("=" * 70)
        print("✅ MIGRATION COMPLETED SUCCESSFULLY!")
        print("=" * 70)
        print()
        print("Next steps:")
        print("  1. Looker views will now work correctly")
        print("  2. Images/documents are in the same database as exhibitors")
        print("  3. Old medica database can be kept for backup")

    finally:
        await conn_new.close()


if __name__ == "__main__":
    asyncio.run(migrate_tables())
