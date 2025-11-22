# CMEF Catalog Processing Module

Extract, classify, and enrich medical equipment manufacturer data from the CMEF 2025 catalog PDF.

## Implementation Summary

**Status**: ✅ Complete and ready to use

This comprehensive module processes the 274 MB CMEF 2025 catalog PDF to extract structured data on Chinese medical equipment manufacturers, with intelligent classification and Brazilian market integration.

### Module Structure

```
CMEF/
├── __init__.py                     # Module initialization
├── config.py                       # Configuration & constants
├── README.md                       # This file
├── run_pipeline.sh                 # Quick start script
│
├── Step Scripts (Main Pipeline)
│   ├── step1_ocr_extraction.py     # PDF → Text via DeepSeek OCR
│   ├── step2_parse_and_structure.py # Text → Structured data via Gemini
│   ├── step3_classify_enrich.py    # Add NCM codes & risk classes
│   └── step4_save_database.py      # Save to PostgreSQL
│
├── utils/                          # Utility modules
│   ├── pdf_preprocessor.py         # Image preprocessing
│   ├── deepseek_client.py          # DeepSeek OCR API client
│   ├── gemini_client.py            # Gemini parsing client
│   ├── ncm_mapper.py               # NCM & risk classification
│   └── validator.py                # Data validation & website checking
│
├── config/
│   └── ncm_mappings.json           # NCM code mappings
│
├── data/                           # Output directory (created at runtime)
└── logs/                           # Log files (created at runtime)
```

### Key Features

**1. OCR Processing (DeepSeek + Tesseract Fallback)**
- Batch processing for large PDFs (15 pages per batch)
- Image preprocessing (denoising, contrast enhancement)
- Support for both DeepSeek OCR (cloud) and Tesseract (local)
- Progress tracking with ETA

**2. AI-Powered Parsing (Gemini 2.0 Flash)**
- Intelligent field extraction from OCR text
- Hybrid approach: AI + regex fallbacks
- Batch processing for API efficiency
- Handles bilingual text (English + Chinese)

**3. Smart Classification**
- Product category inference using Gemini
- NCM code assignment (22 medical categories mapped)
- ANVISA risk classification (Class I/II/III)
- Confidence scoring for all classifications

**4. Data Validation**
- Email format validation
- Website URL cleaning and accessibility checking
- Booth number format validation
- Special focus on Class III (high-risk) companies

**5. Database Integration**
- PostgreSQL schema with proper indexing
- Batch inserts for performance
- Summary statistics generation
- Integration with existing Medical project database

### Processing Estimates

For CMEF_2025.pdf (274 MB, ~500 pages):

| Phase | Time | Cost |
|-------|------|------|
| OCR Extraction | 2-4 hours | $10-20 |
| Parsing | 30-60 min | $2-5 |
| Classification | 15-30 min | $1-3 |
| Database | 5-10 min | Free |
| **Total** | **3-5 hours** | **$13-28** |

### Quick Start Commands

**Test Mode (10 pages, local OCR):**
```bash
cd /Users/gabrielreginatto/Desktop/Code/Medical/CMEF
./run_pipeline.sh --test
```

**Full Processing:**
```bash
# 1. Set up API keys
echo "GEMINI_API_KEY=your_key" > .env

# 2. Run full pipeline
./run_pipeline.sh
```

## Overview

This module processes the CMEF (China Medical Equipment Fair) catalog to create a structured database of medical equipment manufacturers with:
- Company contact information (name, address, email, website)
- Product classifications (categories and subcategories)
- Brazilian NCM tax codes
- ANVISA risk classifications (Class I/II/III)
- Website validation status

## Architecture

### Pipeline Steps

1. **Step 1: OCR Extraction** (`step1_ocr_extraction.py`)
   - Converts PDF pages to images
   - Applies preprocessing (denoising, contrast enhancement)
   - Runs DeepSeek OCR via Vertex AI
   - Saves raw OCR text with metadata

2. **Step 2: Parse & Structure** (`step2_parse_and_structure.py`)
   - Parses OCR text using Gemini AI
   - Extracts structured company data
   - Validates fields (email, website, booth number)
   - Checks website accessibility

3. **Step 3: Classify & Enrich** (`step3_classify_enrich.py`)
   - Classifies products into medical categories
   - Assigns NCM codes
   - Determines ANVISA risk class
   - Generates classification statistics

4. **Step 4: Save to Database** (`step4_save_database.py`)
   - Creates PostgreSQL table schema
   - Inserts enriched company data
   - Creates indexes for fast querying

## Prerequisites

### 1. Install Dependencies

```bash
pip install pdf2image pillow opencv-python PyPDF2
pip install google-cloud-aiplatform google-generativeai
pip install psycopg2-binary aiohttp python-dotenv
```

### 2. System Requirements

- **Tesseract OCR** (for local fallback): `brew install tesseract`
- **Poppler** (for PDF processing): `brew install poppler`

### 3. API Setup

#### DeepSeek OCR (Vertex AI)

Deploy DeepSeek OCR model:

```bash
gcloud ai model-garden models deploy \
  --model=deepseek-ai/deepseek-ocr-maas \
  --region=us-central1 \
  --machine-type=g2-standard-8 \
  --accelerator-type=NVIDIA_L4 \
  --accelerator-count=1 \
  --endpoint-display-name=deepseek-ocr-endpoint
```

#### Gemini API

Create `.env` file in CMEF directory:

```bash
GEMINI_API_KEY=your_gemini_api_key_here
```

Get API key from: https://aistudio.google.com/app/apikey

## Usage

### Quick Start

Process the entire catalog:

```bash
cd /Users/gabrielreginatto/Desktop/Code/Medical/CMEF

# Step 1: Extract text (2-4 hours)
python3 step1_ocr_extraction.py

# Step 2: Parse companies (30-60 minutes)
python3 step2_parse_and_structure.py

# Step 3: Classify and enrich (15-30 minutes)
python3 step3_classify_enrich.py

# Step 4: Save to database (5-10 minutes)
python3 step4_save_database.py
```

### Testing with Sample Pages

Test with first 20 pages:

```bash
python3 step1_ocr_extraction.py --max-pages 20 --local-ocr
```

Options:
- `--max-pages N`: Process only first N pages
- `--local-ocr`: Use Tesseract instead of DeepSeek (faster, lower quality)
- `--cleanup`: Delete temporary image files after processing

### Development Mode

Use local OCR for testing (no Vertex AI required):

```bash
python3 step1_ocr_extraction.py --local-ocr --max-pages 10
```

## Output Files

All outputs saved to `CMEF/data/`:

- `ocr_raw_output.json` - Raw OCR text from DeepSeek
- `structured_companies.json` - Parsed company data
- `enriched_companies.json` - With NCM codes and classifications
- `validation_report.json` - Data quality report

Logs saved to `CMEF/logs/`:

- `ocr_extraction.log`
- `parsing.log`
- `classification.log`
- `database.log`

## Database Schema

Table: `cmef_companies`

```sql
CREATE TABLE cmef_companies (
    id SERIAL PRIMARY KEY,
    company_name_en VARCHAR(500),
    company_name_zh VARCHAR(500),
    booth_number VARCHAR(50),
    address TEXT,
    email VARCHAR(255),
    website VARCHAR(500),
    phone VARCHAR(100),
    scope_description TEXT,
    product_category VARCHAR(200),
    product_subcategory VARCHAR(200),
    category_confidence FLOAT,
    ncm_code VARCHAR(20),
    risk_class VARCHAR(10),
    risk_confidence FLOAT,
    website_validated BOOLEAN,
    website_status_code INTEGER,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

## Configuration

Edit `config.py` to customize:

- `PAGES_PER_BATCH`: Pages per OCR batch (default: 15)
- `GEMINI_BATCH_SIZE`: Companies per Gemini API call (default: 20)
- `VALIDATE_WEBSITES`: Enable website validation (default: True)
- `MAX_CONCURRENT_VALIDATIONS`: Parallel website checks (default: 10)

### Custom NCM Mappings

Edit `config/ncm_mappings.json` to add custom category → NCM code mappings:

```json
{
  "ncm_mappings": {
    "Custom Category": "9018.XX.XX"
  },
  "risk_rules": {
    "III": ["custom_keyword"]
  }
}
```

## Troubleshooting

### DeepSeek OCR Not Working

**Error**: "Endpoint not found"

**Solution**: Deploy the model first:

```bash
gcloud ai endpoints list --region=us-central1
```

If endpoint missing, run deployment command (see API Setup above).

**Alternative**: Use local OCR for testing:

```bash
python3 step1_ocr_extraction.py --local-ocr
```

### Gemini API Rate Limits

**Error**: "ResourceExhausted" or "429 Too Many Requests"

**Solution**: Reduce `GEMINI_BATCH_SIZE` in `config.py`:

```python
GEMINI_BATCH_SIZE = 10  # Reduce from 20
```

### PDF Too Large

**Error**: "PDF file size exceeds maximum"

**Solution**: The pipeline automatically processes in batches. No action needed.

### Memory Issues

If system runs out of memory:

1. Reduce `PAGES_PER_BATCH` in `config.py`
2. Process PDF in smaller chunks
3. Enable `--cleanup` flag to remove temp images

## Performance

### Estimated Processing Time

For CMEF 2025 PDF (274 MB, ~500 pages):

| Step | Time | Cost |
|------|------|------|
| Step 1: OCR | 2-4 hours | $10-20 (DeepSeek) |
| Step 2: Parsing | 30-60 min | $2-5 (Gemini) |
| Step 3: Classification | 15-30 min | $1-3 (Gemini) |
| Step 4: Database | 5-10 min | Free |
| **Total** | **3-5 hours** | **$13-28** |

### Optimization Tips

1. **Use batch processing** (already configured)
2. **Process during off-peak hours** (cheaper GPU quota)
3. **Test with `--max-pages` first** to validate setup
4. **Enable `--cleanup`** to save disk space

## Integration with PNCP Module

After completing CMEF processing, integrate with tender matching:

```python
# Match PNCP tender items to CMEF companies
from CMEF.utils.ncm_mapper import NCMMapper
from ai_matching.step2_gemini import GeminiMatcher

# Load CMEF companies
with open('CMEF/data/enriched_companies.json') as f:
    cmef_companies = json.load(f)

# Match by NCM code
for item in tender_items:
    matching_companies = [
        c for c in cmef_companies
        if c['ncm_code'] == item['ncm_code']
    ]
```

## Next Steps

1. **Create Looker Dashboard** for CMEF company analysis
2. **Build supplier recommendation system** (CMEF ↔ PNCP matching)
3. **Add automated email validation** (SMTP verification)
4. **Integrate with CRM** (export to Salesforce/HubSpot)

## Support

For issues or questions:
- Check logs in `CMEF/logs/`
- Review validation report in `data/validation_report.json`
- See main project README for database connection issues

## License

Part of the Medical PNCP Integration System
