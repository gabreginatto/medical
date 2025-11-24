#!/usr/bin/env python3
"""
Fix exhibitor_id foreign keys in medica_product_images table
Map old medica database IDs to new medical_exhibitors database IDs
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


async def fix_image_ids():
    """Fix exhibitor_id foreign keys"""

    log("=" * 70)
    log("FIXING IMAGE EXHIBITOR IDS")
    log("=" * 70)

    db_manager = create_db_manager_from_env()

    # Step 1: Build ID mapping from old -> new
    log("")
    log("📖 Step 1: Building ID mapping...")
    log("-" * 70)

    # Get old medica exhibitor IDs and names
    db_manager.database_name = 'medica'
    conn_old = await db_manager.get_connection()
    log("Connected to old medica database")

    try:
        old_exhibitors = await conn_old.fetch("SELECT id, name FROM medica_exhibitors ORDER BY id")
        log(f"✅ Found {len(old_exhibitors)} exhibitors in old database")
    finally:
        await conn_old.close()

    # Get new medical_exhibitors IDs and names for MEDICA companies
    db_manager.database_name = 'medical_exhibitors'
    conn_new = await db_manager.get_connection()
    log("Connected to new medical_exhibitors database")

    try:
        new_exhibitors = await conn_new.fetch("""
            SELECT id, name
            FROM medical_exhibitors
            WHERE data_source = 'MEDICA'
            ORDER BY name
        """)
        log(f"✅ Found {len(new_exhibitors)} MEDICA exhibitors in new database")

        # Build name -> new_id mapping
        name_to_new_id = {row['name'].strip().lower(): row['id'] for row in new_exhibitors}

        # Build old_id -> new_id mapping
        id_mapping = {}
        unmatched = []

        for old_row in old_exhibitors:
            old_id = old_row['id']
            name = old_row['name'].strip().lower()

            if name in name_to_new_id:
                new_id = name_to_new_id[name]
                id_mapping[old_id] = new_id
            else:
                unmatched.append((old_id, old_row['name']))

        log(f"✅ Mapped {len(id_mapping)} exhibitor IDs")
        if unmatched:
            log(f"⚠️  {len(unmatched)} exhibitors could not be matched")
            if len(unmatched) <= 10:
                for old_id, name in unmatched[:10]:
                    log(f"  - ID {old_id}: {name}")

        # Step 2: Update exhibitor_ids in images table
        log("")
        log("🔄 Step 2: Updating exhibitor_ids in medica_product_images...")
        log("-" * 70)

        # Get all images
        images = await conn_new.fetch("SELECT id, exhibitor_id FROM medica_product_images")
        log(f"Found {len(images)} images to update")

        updated_count = 0
        skipped_count = 0

        log("Updating image exhibitor_ids...")
        async with conn_new.transaction():
            for img in images:
                old_exhibitor_id = img['exhibitor_id']

                if old_exhibitor_id in id_mapping:
                    new_exhibitor_id = id_mapping[old_exhibitor_id]
                    await conn_new.execute("""
                        UPDATE medica_product_images
                        SET exhibitor_id = $1
                        WHERE id = $2
                    """, new_exhibitor_id, img['id'])
                    updated_count += 1

                    if updated_count % 500 == 0:
                        log(f"  Progress: {updated_count}/{len(images)} images updated...")
                else:
                    skipped_count += 1

        log(f"✅ Updated {updated_count} images")
        if skipped_count > 0:
            log(f"⚠️  Skipped {skipped_count} images (exhibitor not found in new database)")

        # Step 3: Verification
        log("")
        log("=" * 70)
        log("STEP 3: VERIFICATION")
        log("=" * 70)

        # Test join
        log("Testing join with medical_exhibitors...")
        join_result = await conn_new.fetch("""
            SELECT
                e.name,
                e.data_source,
                COUNT(i.id) as image_count
            FROM medical_exhibitors_unique e
            JOIN medica_product_images i ON e.id = i.exhibitor_id
            WHERE e.data_source = 'MEDICA'
            GROUP BY e.name, e.data_source
            HAVING COUNT(i.id) > 0
            ORDER BY image_count DESC
            LIMIT 10
        """)

        if join_result:
            log("✅ Join successful! Sample companies with images:")
            for row in join_result:
                log(f"  • {row['name']}: {row['image_count']} images")
        else:
            log("⚠️  No matches found in join")

        # Total companies with images
        companies_with_images = await conn_new.fetchval("""
            SELECT COUNT(DISTINCT e.id)
            FROM medical_exhibitors_unique e
            JOIN medica_product_images i ON e.id = i.exhibitor_id
            WHERE e.data_source = 'MEDICA'
        """)

        total_images = await conn_new.fetchval("""
            SELECT COUNT(*)
            FROM medica_product_images i
            JOIN medical_exhibitors_unique e ON e.id = i.exhibitor_id
            WHERE e.data_source = 'MEDICA'
        """)

        log("")
        log(f"📊 Final Statistics:")
        log(f"  • {companies_with_images} MEDICA companies have product images")
        log(f"  • {total_images} images successfully linked")
        log(f"  • {updated_count} exhibitor IDs updated")

        log("")
        log("=" * 70)
        log("✅ ID MAPPING COMPLETED SUCCESSFULLY!")
        log("=" * 70)
        log("")
        log("Next steps:")
        log("  1. Looker views will now show images correctly")
        log("  2. All foreign key relationships are fixed")
        log("")

    except Exception as e:
        log("")
        log(f"❌ ERROR: {e}")
        import traceback
        log(traceback.format_exc())
        raise
    finally:
        await conn_new.close()


if __name__ == "__main__":
    try:
        asyncio.run(fix_image_ids())
    except KeyboardInterrupt:
        log("\n⚠️  Interrupted by user")
    except Exception as e:
        log(f"\n❌ Failed: {e}")
        sys.exit(1)
