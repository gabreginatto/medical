#!/bin/bash
# CMEF Catalog Processing Pipeline
# Quick start script to run all steps

set -e  # Exit on error

echo "========================================"
echo "CMEF Catalog Processing Pipeline"
echo "========================================"
echo ""

# Change to CMEF directory
cd "$(dirname "$0")"

# Create necessary directories
mkdir -p data logs config

# Check for .env file
if [ ! -f .env ]; then
    echo "⚠️  Warning: .env file not found!"
    echo "Please create .env with:"
    echo "GEMINI_API_KEY=your_api_key_here"
    echo ""
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Parse arguments
MAX_PAGES=""
LOCAL_OCR=""
CLEANUP=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --max-pages)
            MAX_PAGES="--max-pages $2"
            shift 2
            ;;
        --local-ocr)
            LOCAL_OCR="--local-ocr"
            shift
            ;;
        --cleanup)
            CLEANUP="--cleanup"
            shift
            ;;
        --test)
            MAX_PAGES="--max-pages 10"
            LOCAL_OCR="--local-ocr"
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--max-pages N] [--local-ocr] [--cleanup] [--test]"
            exit 1
            ;;
    esac
done

# Step 1: OCR Extraction
echo "========================================"
echo "Step 1: OCR Extraction"
echo "========================================"
python3 step1_ocr_extraction.py $MAX_PAGES $LOCAL_OCR $CLEANUP
echo ""

# Step 2: Parse and Structure
echo "========================================"
echo "Step 2: Parse and Structure"
echo "========================================"
python3 step2_parse_and_structure.py
echo ""

# Step 3: Classify and Enrich
echo "========================================"
echo "Step 3: Classify and Enrich"
echo "========================================"
python3 step3_classify_enrich.py
echo ""

# Step 4: Save to Database
echo "========================================"
echo "Step 4: Save to Database"
echo "========================================"
python3 step4_save_database.py
echo ""

echo "========================================"
echo "✅ Pipeline Complete!"
echo "========================================"
echo ""
echo "Results saved to:"
echo "  - data/ocr_raw_output.json"
echo "  - data/structured_companies.json"
echo "  - data/enriched_companies.json"
echo "  - PostgreSQL table: cmef_companies"
echo ""
echo "Logs saved to:"
echo "  - logs/ocr_extraction.log"
echo "  - logs/parsing.log"
echo "  - logs/classification.log"
echo "  - logs/database.log"
echo ""
