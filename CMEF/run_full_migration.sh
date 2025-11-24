#!/bin/bash

# =============================================================================
# Unified Medical Database - Full Migration Script
# =============================================================================
# This script runs the complete migration process from start to finish.
# It safely creates a new database and migrates data without touching the
# existing 'medical' database.
# =============================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_step() {
    echo -e "${BLUE}===================================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}===================================================================${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# =============================================================================
# Step 0: Pre-flight checks
# =============================================================================

print_step "STEP 0: Pre-flight Checks"

# Check if required files exist
echo "Checking required files..."
required_files=(
    "create_unified_database.sql"
    "migrate_medica_to_unified.py"
    "import_cmef_to_unified.py"
    "classify_unified_companies.py"
    "data/enriched_companies.json"
)

for file in "${required_files[@]}"; do
    if [ ! -f "$file" ]; then
        print_error "Required file not found: $file"
        exit 1
    fi
done
print_success "All required files found"

# Check if logs directory exists
if [ ! -d "logs" ]; then
    mkdir -p logs
    print_success "Created logs directory"
fi

# =============================================================================
# Step 1: Get database connection strings
# =============================================================================

print_step "STEP 1: Database Configuration"

echo ""
echo "Please provide database connection strings:"
echo ""
echo "Format: postgresql://user:password@host:5432/database_name"
echo ""

# Source database (old medical database - READ ONLY)
if [ -z "$SOURCE_DB_URL" ]; then
    echo -n "Source database URL (old 'medical' database): "
    read SOURCE_DB_URL
fi
export SOURCE_DB_URL

# Target database (new medical_unified database)
if [ -z "$TARGET_DB_URL" ]; then
    echo -n "Target database URL (new 'medical_unified' database): "
    read TARGET_DB_URL
fi
export TARGET_DB_URL
export UNIFIED_DB_URL="$TARGET_DB_URL"

print_success "Database URLs configured"

# =============================================================================
# Step 2: Confirm migration plan
# =============================================================================

print_step "STEP 2: Migration Plan Confirmation"

echo ""
echo "📖 Source (READ ONLY): ${SOURCE_DB_URL#*@}"
echo "💾 Target (NEW): ${TARGET_DB_URL#*@}"
echo ""
echo "This script will:"
echo "  1. Create schema in new database"
echo "  2. Migrate ~1,321 MEDICA companies (read-only from source)"
echo "  3. Import ~4,497 CMEF companies from enriched_companies.json"
echo "  4. Classify all companies using Gemini AI"
echo ""
print_warning "The original 'medical' database will NOT be modified"
echo ""
echo -n "Proceed with migration? (yes/no): "
read confirm

if [ "$confirm" != "yes" ]; then
    print_error "Migration cancelled by user"
    exit 0
fi

# =============================================================================
# Step 3: Create database schema
# =============================================================================

print_step "STEP 3: Creating Database Schema"

echo "Extracting connection details..."
DB_HOST=$(echo $TARGET_DB_URL | sed -n 's/.*@\([^:]*\):.*/\1/p')
DB_PORT=$(echo $TARGET_DB_URL | sed -n 's/.*:\([0-9]*\)\/.*/\1/p')
DB_NAME=$(echo $TARGET_DB_URL | sed -n 's/.*\/\([^?]*\).*/\1/p')
DB_USER=$(echo $TARGET_DB_URL | sed -n 's/.*:\/\/\([^:]*\):.*/\1/p')

echo "Executing create_unified_database.sql..."
PGPASSWORD=$(echo $TARGET_DB_URL | sed -n 's/.*:\/\/[^:]*:\([^@]*\)@.*/\1/p') \
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
    -f create_unified_database.sql \
    2>&1 | tee logs/schema_creation.log

if [ $? -eq 0 ]; then
    print_success "Schema created successfully"
else
    print_error "Schema creation failed. Check logs/schema_creation.log"
    exit 1
fi

# Verify schema
echo "Verifying schema..."
TABLE_COUNT=$(PGPASSWORD=$(echo $TARGET_DB_URL | sed -n 's/.*:\/\/[^:]*:\([^@]*\)@.*/\1/p') \
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
    -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'medical_exhibitors';")

if [ "$TABLE_COUNT" -eq 1 ]; then
    print_success "Table 'medical_exhibitors' created"
else
    print_error "Table verification failed"
    exit 1
fi

# =============================================================================
# Step 4: Migrate MEDICA data
# =============================================================================

print_step "STEP 4: Migrating MEDICA Data"

echo "Starting MEDICA migration (READ ONLY from source)..."
python3 migrate_medica_to_unified.py <<EOF
yes
EOF

if [ $? -eq 0 ]; then
    print_success "MEDICA data migrated successfully"
else
    print_error "MEDICA migration failed"
    exit 1
fi

# Verify MEDICA migration
echo "Verifying MEDICA migration..."
MEDICA_COUNT=$(PGPASSWORD=$(echo $TARGET_DB_URL | sed -n 's/.*:\/\/[^:]*:\([^@]*\)@.*/\1/p') \
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
    -t -c "SELECT COUNT(*) FROM medical_exhibitors WHERE data_source = 'MEDICA';")

echo "MEDICA companies in new database: $MEDICA_COUNT"
if [ "$MEDICA_COUNT" -gt 0 ]; then
    print_success "MEDICA migration verified ($MEDICA_COUNT companies)"
else
    print_error "MEDICA migration verification failed"
    exit 1
fi

# =============================================================================
# Step 5: Import CMEF data
# =============================================================================

print_step "STEP 5: Importing CMEF Data"

echo "Starting CMEF import..."
python3 import_cmef_to_unified.py <<EOF
yes
EOF

if [ $? -eq 0 ]; then
    print_success "CMEF data imported successfully"
else
    print_error "CMEF import failed"
    exit 1
fi

# Verify CMEF import
echo "Verifying CMEF import..."
CMEF_COUNT=$(PGPASSWORD=$(echo $TARGET_DB_URL | sed -n 's/.*:\/\/[^:]*:\([^@]*\)@.*/\1/p') \
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
    -t -c "SELECT COUNT(*) FROM medical_exhibitors WHERE data_source = 'CMEF';")

echo "CMEF companies in new database: $CMEF_COUNT"
if [ "$CMEF_COUNT" -gt 0 ]; then
    print_success "CMEF import verified ($CMEF_COUNT companies)"
else
    print_error "CMEF import verification failed"
    exit 1
fi

# =============================================================================
# Step 6: Classify companies
# =============================================================================

print_step "STEP 6: Classifying Companies with AI"

echo "Starting classification (this may take 2-3 minutes)..."
python3 classify_unified_companies.py <<EOF
1
yes
EOF

if [ $? -eq 0 ]; then
    print_success "Classification completed successfully"
else
    print_warning "Classification completed with some errors (this is normal)"
fi

# =============================================================================
# Step 7: Final verification
# =============================================================================

print_step "STEP 7: Final Verification"

echo "Running final checks..."

# Total count
TOTAL_COUNT=$(PGPASSWORD=$(echo $TARGET_DB_URL | sed -n 's/.*:\/\/[^:]*:\([^@]*\)@.*/\1/p') \
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
    -t -c "SELECT COUNT(*) FROM medical_exhibitors;")

# Classified count
CLASSIFIED_COUNT=$(PGPASSWORD=$(echo $TARGET_DB_URL | sed -n 's/.*:\/\/[^:]*:\([^@]*\)@.*/\1/p') \
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
    -t -c "SELECT COUNT(*) FROM medical_exhibitors WHERE product_category IS NOT NULL;")

# Calculate percentage
CLASSIFIED_PCT=$(echo "scale=1; $CLASSIFIED_COUNT * 100 / $TOTAL_COUNT" | bc)

echo ""
echo "==================================================================="
echo "                    MIGRATION SUMMARY"
echo "==================================================================="
echo ""
echo "  📊 Total Companies:      $TOTAL_COUNT"
echo "  🔵 MEDICA Companies:     $MEDICA_COUNT"
echo "  🟢 CMEF Companies:       $CMEF_COUNT"
echo "  🤖 Classified:           $CLASSIFIED_COUNT ($CLASSIFIED_PCT%)"
echo ""
echo "==================================================================="

if [ "$TOTAL_COUNT" -gt 5000 ] && [ "$CLASSIFIED_COUNT" -gt 5000 ]; then
    print_success "Migration completed successfully!"
    echo ""
    echo "✅ Verification passed all checks"
    echo "✅ Original 'medical' database untouched"
    echo "✅ New 'medical_unified' database ready"
    echo ""
    echo "Next steps:"
    echo "  1. Update Looker connection to point to 'medical_unified'"
    echo "  2. Review logs in logs/ directory"
    echo "  3. Test queries in MIGRATION_GUIDE.md"
    echo ""
else
    print_error "Verification failed - counts are lower than expected"
    echo "Expected: ~5,800 total, ~5,800 classified"
    echo "Got: $TOTAL_COUNT total, $CLASSIFIED_COUNT classified"
    exit 1
fi

# =============================================================================
# Done!
# =============================================================================

print_step "🎉 MIGRATION COMPLETE!"

echo ""
echo "All logs saved to:"
echo "  - logs/schema_creation.log"
echo "  - logs/medica_migration.log"
echo "  - logs/cmef_unified_import.log"
echo "  - logs/unified_classification.log"
echo ""
echo "For detailed usage examples, see: MIGRATION_GUIDE.md"
echo ""

exit 0
