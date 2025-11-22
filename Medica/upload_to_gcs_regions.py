#!/usr/bin/env python3
"""
Upload MEDICA exhibitor images and documents to Google Cloud Storage
Handles China and Global regions separately
"""
import os
import json
import argparse
from google.cloud import storage
from pathlib import Path
import mimetypes

# Configuration
PROJECT_ID = "medical-473219"
BUCKET_NAME = "medica-exhibitor-data"

def upload_file_to_gcs(bucket, local_path, gcs_path):
    """Upload a single file to GCS"""
    blob = bucket.blob(gcs_path)

    # Set content type
    content_type, _ = mimetypes.guess_type(local_path)
    if content_type:
        blob.content_type = content_type

    # Upload
    blob.upload_from_filename(local_path)

    return f"gs://{bucket.name}/{gcs_path}"

def upload_region_files(region="china", downloads_dir="downloads"):
    """
    Upload exhibitor files from a specific region (china or global)

    Args:
        region: "china" or "global"
        downloads_dir: Base downloads directory

    Returns:
        List of exhibitor data with GCS URLs
    """
    region_lower = region.lower()
    region_folder = "China" if region_lower == "china" else "Global"
    region_path = os.path.join(downloads_dir, region_folder)

    if not os.path.exists(region_path):
        print(f"❌ Error: Region folder not found: {region_path}")
        return []

    print(f"\n{'='*60}")
    print(f"UPLOADING {region.upper()} EXHIBITOR FILES TO GCS")
    print(f"{'='*60}")
    print(f"Source: {region_path}")
    print(f"Bucket: gs://{BUCKET_NAME}/")
    print(f"Region path: {region_lower}/")
    print()

    # Initialize GCS client
    storage_client = storage.Client(project=PROJECT_ID)
    bucket = storage_client.bucket(BUCKET_NAME)

    # Scan exhibitor folders
    exhibitor_folders = [
        f for f in Path(region_path).iterdir()
        if f.is_dir()
    ]

    print(f"Found {len(exhibitor_folders)} exhibitor folders\n")

    uploaded_data = []
    total_images = 0
    total_docs = 0
    total_size = 0
    skipped = 0

    for idx, exhibitor_folder in enumerate(sorted(exhibitor_folders), 1):
        exhibitor_name = exhibitor_folder.name
        info_file = exhibitor_folder / "info.json"

        # Skip if no info.json
        if not info_file.exists():
            print(f"[{idx}/{len(exhibitor_folders)}] ⚠️  Skipping {exhibitor_name} - No info.json")
            skipped += 1
            continue

        # Load exhibitor info
        try:
            with open(info_file, 'r', encoding='utf-8') as f:
                exhibitor_data = json.load(f)
        except Exception as e:
            print(f"[{idx}/{len(exhibitor_folders)}] ✗ Error reading {exhibitor_name}/info.json: {e}")
            skipped += 1
            continue

        print(f"[{idx}/{len(exhibitor_folders)}] Processing: {exhibitor_name}")

        # Add GCS URL fields
        exhibitor_data['product_image_gcs_urls'] = []
        exhibitor_data['document_gcs_urls'] = []

        # Upload product images
        images_uploaded = 0
        for img_file in sorted(exhibitor_folder.glob("*.jpg")) + sorted(exhibitor_folder.glob("*.jpeg")) + sorted(exhibitor_folder.glob("*.png")):
            if img_file.name == "info.json":
                continue

            filename = img_file.name
            # GCS path: china/images/{company}/{filename} or global/images/{company}/{filename}
            gcs_path = f"{region_lower}/images/{exhibitor_name}/{filename}"

            try:
                url = upload_file_to_gcs(bucket, str(img_file), gcs_path)
                file_size = img_file.stat().st_size

                exhibitor_data['product_image_gcs_urls'].append({
                    'filename': filename,
                    'gcs_url': url,
                    'gcs_bucket': BUCKET_NAME,
                    'gcs_path': gcs_path,
                    'order': images_uploaded + 1,
                    'file_size_bytes': file_size
                })

                images_uploaded += 1
                total_images += 1
                total_size += file_size
            except Exception as e:
                print(f"  ✗ Error uploading {filename}: {e}")

        if images_uploaded > 0:
            print(f"  ✓ Uploaded {images_uploaded} images")

        # Upload documents (PDFs, etc.)
        docs_uploaded = 0
        for doc_file in sorted(exhibitor_folder.glob("*.pdf")):
            filename = doc_file.name
            # GCS path: china/documents/{company}/{filename} or global/documents/{company}/{filename}
            gcs_path = f"{region_lower}/documents/{exhibitor_name}/{filename}"

            try:
                url = upload_file_to_gcs(bucket, str(doc_file), gcs_path)
                file_size = doc_file.stat().st_size

                exhibitor_data['document_gcs_urls'].append({
                    'filename': filename,
                    'gcs_url': url,
                    'gcs_bucket': BUCKET_NAME,
                    'gcs_path': gcs_path,
                    'file_size_bytes': file_size
                })

                docs_uploaded += 1
                total_docs += 1
                total_size += file_size
            except Exception as e:
                print(f"  ✗ Error uploading {filename}: {e}")

        if docs_uploaded > 0:
            print(f"  ✓ Uploaded {docs_uploaded} documents")

        uploaded_data.append(exhibitor_data)

    # Save updated data with GCS URLs
    output_file = f"{region_lower}_exhibitors_with_gcs_urls.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(uploaded_data, f, indent=2, ensure_ascii=False)

    print(f"\n{'='*60}")
    print(f"UPLOAD COMPLETE - {region.upper()}")
    print(f"{'='*60}")
    print(f"Total exhibitors processed: {len(uploaded_data)}")
    print(f"Skipped (no info.json): {skipped}")
    print(f"Total images uploaded: {total_images}")
    print(f"Total documents uploaded: {total_docs}")
    print(f"Total size: {total_size / 1024 / 1024:.2f} MB")
    print(f"GCS path: gs://{BUCKET_NAME}/{region_lower}/")
    print(f"Data saved to: {output_file}")
    print(f"{'='*60}\n")

    return uploaded_data

def main():
    parser = argparse.ArgumentParser(description="Upload MEDICA exhibitor files to GCS by region")
    parser.add_argument(
        "--region",
        choices=["china", "global", "both"],
        default="both",
        help="Which region to upload (china, global, or both)"
    )
    parser.add_argument(
        "--downloads-dir",
        default="downloads",
        help="Base downloads directory (default: downloads)"
    )

    args = parser.parse_args()

    if args.region in ["china", "both"]:
        upload_region_files("china", args.downloads_dir)

    if args.region in ["global", "both"]:
        upload_region_files("global", args.downloads_dir)

if __name__ == "__main__":
    main()
