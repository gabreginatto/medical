#!/bin/bash
# Apply schema.sql to medica database using gcloud and Cloud Shell

set -e

INSTANCE="pncp-medical-db"
DATABASE="medica"
SCHEMA_FILE="schema.sql"

echo "=================================================="
echo "Applying schema to Cloud SQL database"
echo "=================================================="
echo "Instance: $INSTANCE"
echo "Database: $DATABASE"
echo "Schema file: $SCHEMA_FILE"
echo ""

# Check if schema file exists
if [ ! -f "$SCHEMA_FILE" ]; then
    echo "❌ Error: $SCHEMA_FILE not found"
    exit 1
fi

echo "Uploading schema to temporary Cloud Storage location..."
BUCKET="gs://medica-exhibitor-data"
TIMESTAMP=$(date +%s)
GCS_PATH="$BUCKET/temp/medica-schema-$TIMESTAMP.sql"

# Upload to GCS
gsutil cp "$SCHEMA_FILE" "$GCS_PATH"
echo "✓ Uploaded to $GCS_PATH"

# Import SQL file to Cloud SQL
echo ""
echo "Importing schema to Cloud SQL..."
gcloud sql import sql "$INSTANCE" "$GCS_PATH" \
    --database="$DATABASE" \
    --quiet

echo ""
echo "✓ Schema applied successfully!"

# Clean up
echo "Cleaning up temporary file..."
gsutil rm "$GCS_PATH"

echo ""
echo "=================================================="
echo "✅ SCHEMA APPLICATION COMPLETE"
echo "=================================================="
