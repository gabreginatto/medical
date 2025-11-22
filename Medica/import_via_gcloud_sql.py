#!/usr/bin/env python3
"""
Import MEDICA exhibitor data into Cloud SQL PostgreSQL
Uses gcloud SQL connection (no password needed)
"""
import os
import sys
import json
import subprocess
import tempfile
import argparse

def create_import_sql(data_file, region="china"):
    """
    Create SQL statements from JSON data

    Args:
        data_file: JSON file with GCS URLs
        region: "china" or "global"

    Returns:
        SQL string to execute
    """
    region_name = region.capitalize()

    print(f"\nLoading data from {data_file}...")
    with open(data_file, 'r', encoding='utf-8') as f:
        exhibitors = json.load(f)

    print(f"Found {len(exhibitors)} exhibitors to import\n")

    sql_statements = []

    for idx, exhibitor in enumerate(exhibitors, 1):
        name = exhibitor.get('name', f'Unknown_{idx}')
        # Escape single quotes in strings for SQL
        name_escaped = name.replace("'", "''")

        location = (exhibitor.get('location') or '').replace("'", "''")
        description = (exhibitor.get('company_description') or '').replace("'", "''")
        email = (exhibitor.get('email') or '').replace("'", "''") if exhibitor.get('email') else ''
        phone = (exhibitor.get('phone') or '').replace("'", "''") if exhibitor.get('phone') else ''
        website = (exhibitor.get('website') or '').replace("'", "''") if exhibitor.get('website') else ''
        address = (exhibitor.get('address') or '').replace("'", "''") if exhibitor.get('address') else ''
        raw_text = (exhibitor.get('raw_text') or '').replace("'", "''")[:5000]  # Limit size
        country = "China" if region.lower() == "china" else "NULL"
        event = (exhibitor.get('event') or 'MEDICA 2025').replace("'", "''")
        scraped_at = exhibitor.get('scraped_at') or 'NOW()'

        # Insert exhibitor - using WITH clause to capture ID
        sql = f"""
WITH inserted_exhibitor AS (
    INSERT INTO medica_exhibitors
        (name, location, company_description, email, phone, website, address, raw_text, country, region, event, scraped_at)
    VALUES
        ('{name_escaped}', '{location}', '{description}',
         {f"'{email}'" if email else 'NULL'}, {f"'{phone}'" if phone else 'NULL'},
         {f"'{website}'" if website else 'NULL'}, '{address}', '{raw_text}',
         {f"'{country}'" if country != 'NULL' else 'NULL'}, '{region_name}', '{event}', '{scraped_at}')
    RETURNING id
)
"""

        # Add product images
        if 'product_image_gcs_urls' in exhibitor and exhibitor['product_image_gcs_urls']:
            image_values = []
            for img in exhibitor['product_image_gcs_urls']:
                filename = img['filename'].replace("'", "''")
                gcs_url = img['gcs_url'].replace("'", "''")
                gcs_bucket = img['gcs_bucket'].replace("'", "''")
                gcs_path = img['gcs_path'].replace("'", "''")
                order = img.get('order', 1)
                size = img.get('file_size_bytes', 0)

                image_values.append(
                    f"((SELECT id FROM inserted_exhibitor), '{filename}', '{gcs_url}', '{gcs_bucket}', '{gcs_path}', {order}, {size})"
                )

            if image_values:
                sql += f""",
image_insert AS (
    INSERT INTO medica_product_images
        (exhibitor_id, image_filename, gcs_url, gcs_bucket, gcs_path, image_order, file_size_bytes)
    VALUES
        {', '.join(image_values)}
)
"""

        # Add documents
        if 'document_gcs_urls' in exhibitor and exhibitor['document_gcs_urls']:
            doc_values = []
            for doc in exhibitor['document_gcs_urls']:
                filename = doc['filename'].replace("'", "''")
                gcs_url = doc['gcs_url'].replace("'", "''")
                gcs_bucket = doc['gcs_bucket'].replace("'", "''")
                gcs_path = doc['gcs_path'].replace("'", "''")
                size = doc.get('file_size_bytes', 0)

                doc_values.append(
                    f"((SELECT id FROM inserted_exhibitor), '{filename}', '{gcs_url}', '{gcs_bucket}', '{gcs_path}', {size})"
                )

            if doc_values:
                sql += f""",
doc_insert AS (
    INSERT INTO medica_documents
        (exhibitor_id, document_filename, gcs_url, gcs_bucket, gcs_path, file_size_bytes)
    VALUES
        {', '.join(doc_values)}
)
"""

        sql += "\nSELECT id FROM inserted_exhibitor;\n"

        sql_statements.append(sql)

        if idx % 100 == 0:
            print(f"  Processed {idx}/{len(exhibitors)} exhibitors...")

    return '\n'.join(sql_statements)

def import_exhibitors(data_file, region="china"):
    """
    Import exhibitor data using gcloud sql execute

    Args:
        data_file: JSON file with GCS URLs
        region: "china" or "global"
    """
    region_name = region.capitalize()

    print(f"\n{'='*60}")
    print(f"IMPORTING {region.upper()} EXHIBITORS TO CLOUD SQL")
    print(f"{'='*60}")
    print(f"Data file: {data_file}")
    print(f"Database: medica")
    print(f"Region: {region_name}\n")

    # Generate SQL
    print("Generating SQL statements...")
    sql = create_import_sql(data_file, region)

    # Save to temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.sql', delete=False, encoding='utf-8') as f:
        f.write(sql)
        sql_file = f.name

    print(f"SQL file created: {sql_file}")
    print(f"File size: {os.path.getsize(sql_file) / 1024 / 1024:.2f} MB\n")

    # Upload to GCS
    timestamp = int(__import__('time').time())
    gcs_path = f"gs://medica-exhibitor-data/temp/import-{region}-{timestamp}.sql"

    print(f"Uploading SQL to {gcs_path}...")
    result = subprocess.run(
        ['gsutil', 'cp', sql_file, gcs_path],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print(f"❌ Error uploading SQL: {result.stderr}")
        os.unlink(sql_file)
        return

    print("✓ Uploaded\n")

    # Import to Cloud SQL
    print("Importing to Cloud SQL...")
    result = subprocess.run(
        [
            'gcloud', 'sql', 'import', 'sql',
            'pncp-medical-db',
            gcs_path,
            '--database=medica',
            '--quiet'
        ],
        capture_output=True,
        text=True
    )

    # Clean up
    os.unlink(sql_file)
    subprocess.run(['gsutil', 'rm', gcs_path], capture_output=True)

    if result.returncode != 0:
        print(f"❌ Error importing: {result.stderr}")
        return

    print(f"\n{'='*60}")
    print(f"IMPORT COMPLETE - {region.upper()}")
    print(f"{'='*60}\n")

    # Verify
    print("Verifying import...")
    verify_sql = f"SELECT COUNT(*) FROM medica_exhibitors WHERE region = '{region_name}';"

    result = subprocess.run(
        [
            'gcloud', 'sql', 'query',
            'pncp-medical-db',
            '--database=medica',
            f'--sql={verify_sql}'
        ],
        capture_output=True,
        text=True
    )

    print(result.stdout)

def main():
    parser = argparse.ArgumentParser(description="Import MEDICA exhibitor data to Cloud SQL")
    parser.add_argument(
        "--region",
        choices=["china", "global"],
        required=True,
        help="Region to import (china or global)"
    )
    parser.add_argument(
        "--data-file",
        help="Path to JSON data file (optional, defaults to {region}_exhibitors_with_gcs_urls.json)"
    )

    args = parser.parse_args()

    # Default data file if not specified
    data_file = args.data_file or f"{args.region}_exhibitors_with_gcs_urls.json"

    if not os.path.exists(data_file):
        print(f"❌ Error: Data file not found: {data_file}")
        sys.exit(1)

    import_exhibitors(data_file, args.region)

if __name__ == "__main__":
    main()
