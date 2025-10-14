# PNCP Tender Documents Fetcher

Fetches tender documents (Editais), historic price data (Histórico), and price registration records (Atas) from the PNCP API.

## Features

- ✅ **Fetch tender documents** (Editais, attachments, notices)
- ✅ **Download PDF files** to local storage
- ✅ **Fetch price history** (changes, corrections, updates)
- ✅ **Fetch Atas** (price registration records)
- ✅ **Save metadata** to JSON for analysis
- ✅ **Organize by tender** (automatic directory structure)

## Installation

No additional installation required - uses existing project dependencies.

## Usage

### Basic Syntax (Using Control Number - RECOMMENDED)

```bash
python3 scripts/fetch_tender_documents.py --control-number "CNPJ-1-SEQUENTIAL/YEAR"
```

**Example:**
```bash
python3 scripts/fetch_tender_documents.py --control-number "46374500000194-1-006949/2025"
```

### Alternative Syntax (Using Individual Components)

```bash
python3 scripts/fetch_tender_documents.py --cnpj <CNPJ> --year <YEAR> --sequential <SEQ>
```

---

## Examples

### 1. Fetch Metadata Only (No Downloads) - Using Control Number

```bash
python3 scripts/fetch_tender_documents.py \
  --control-number "46374500000194-1-006949/2025"
```

### 1b. Same Using Individual Components

```bash
python3 scripts/fetch_tender_documents.py \
  --cnpj 46374500000194 \
  --year 2025 \
  --sequential 6949
```

**Output:**
- Displays all document metadata
- Shows history records
- Lists Atas (if any)
- Saves JSON metadata to `tender_documents/46374500000194_2025_6949/metadata.json`

### 2. Fetch and Download All Documents

```bash
python3 scripts/fetch_tender_documents.py \
  --control-number "46374500000194-1-006949/2025" \
  --download
```

**Output:**
- Downloads all PDF documents
- Downloads all Ata documents
- Saves to `tender_documents/46374500000194_2025_6949/`

### 3. Custom Output Directory

```bash
python3 scripts/fetch_tender_documents.py \
  --control-number "46374500000194-1-006949/2025" \
  --download \
  --output /path/to/my_documents
```

### 4. Fetch Only Documents (Skip History and Atas)

```bash
# Using short form --control
python3 scripts/fetch_tender_documents.py \
  --control "46374500000194-1-006949/2025" \
  --documents-only
```

### 5. Fetch Only History

```bash
python3 scripts/fetch_tender_documents.py \
  --control "46374500000194-1-006949/2025" \
  --history-only
```

### 6. Fetch Only Atas

```bash
python3 scripts/fetch_tender_documents.py \
  --control "46374500000194-1-006949/2025" \
  --atas-only \
  --download
```

## Command-Line Options

### Primary Options (Choose One)

| Option | Description | Example |
|--------|-------------|---------|
| `--control-number` or `--control` | PNCP control number (CNPJ-1-SEQUENTIAL/YEAR) | `"46374500000194-1-006949/2025"` |
| `--cnpj` + `--year` + `--sequential` | Individual components | See below |

**Note:** You must provide EITHER `--control-number` OR all three individual components.

### Additional Options

| Option | Required | Description |
|--------|----------|-------------|
| `--download` | No | Download document files (PDFs) |
| `--output` | No | Output directory (default: `tender_documents`) |
| `--documents-only` | No | Fetch only documents (skip history and atas) |
| `--history-only` | No | Fetch only history |
| `--atas-only` | No | Fetch only atas |

## Output Structure

```
tender_documents/
└── {CNPJ}_{YEAR}_{SEQUENTIAL}/
    ├── metadata.json                    # Complete metadata (all data)
    ├── {doc_seq}_{doc_title}.pdf        # Downloaded documents
    └── atas/
        └── ata_{ata_seq}_{doc_seq}_{title}.pdf  # Ata documents
```

### Example

```
tender_documents/
└── 46374500000194_2025_6949/
    ├── metadata.json
    ├── 1_09018105904122025000.pdf       # Edital (411 KB)
    └── atas/
        └── (empty if no atas)
```

## Metadata Structure

The `metadata.json` file contains:

```json
{
  "documents": {
    "success": true,
    "count": 1,
    "documents": [
      {
        "uri": "https://pncp.gov.br/pncp-api/v1/...",
        "url": "https://pncp.gov.br/pncp-api/v1/...",
        "sequencialDocumento": 1,
        "titulo": "09018105904122025000",
        "tipoDocumentoNome": "Edital",
        "tipoDocumentoDescricao": "Edital",
        "dataPublicacaoPncp": "2025-07-30T07:18:05",
        "statusAtivo": true
      }
    ]
  },
  "history": {
    "success": true,
    "count": 8,
    "history": [
      {
        "tipoLogManutencaoNome": "Retificação",
        "categoriaLogManutencaoNome": "Item de Contratação",
        "logManutencaoDataInclusao": "2025-09-29T10:54:33",
        "itemNumero": 1,
        "justificativa": "...",
        "documentoTitulo": "...",
        "documentoTipo": "..."
      }
    ]
  },
  "atas": {
    "success": true,
    "count": 0,
    "atas": []
  }
}
```

## Document Types

The API provides access to various document types:

| Type | Description | Example |
|------|-------------|---------|
| **Edital** | Main tender notice | Bidding rules, specifications |
| **Anexo** | Attachments | Technical specs, drawings |
| **Termo de Referência** | Terms of reference | Detailed requirements |
| **Aviso** | Notices | Announcements, updates |
| **Ata** | Price registration record | Framework agreements |
| **Retificação** | Corrections | Document updates |
| **Homologação** | Approval | Award decisions |

## History Record Types

| Type | Description |
|------|-------------|
| **Inclusão** | New item/document added |
| **Retificação** | Correction/update made |
| **Exclusão** | Item/document deleted |

## API Endpoints Used

The script uses these PNCP API endpoints:

1. **Documents List:**
   ```
   GET /v1/orgaos/{cnpj}/compras/{year}/{sequential}/arquivos
   ```

2. **Download Document:**
   ```
   GET /v1/orgaos/{cnpj}/compras/{year}/{sequential}/arquivos/{doc_seq}
   ```

3. **History:**
   ```
   GET /v1/orgaos/{cnpj}/compras/{year}/{sequential}/historico
   ```

4. **Atas List:**
   ```
   GET /v1/orgaos/{cnpj}/compras/{year}/{sequential}/atas
   ```

5. **Ata Documents:**
   ```
   GET /v1/orgaos/{cnpj}/compras/{year}/{sequential}/atas/{ata_seq}/arquivos
   ```

## Finding Tender Identifiers

### Understanding Control Numbers

The **control number** is the unique identifier for each tender in PNCP:

**Format:** `{CNPJ}-1-{SEQUENTIAL}/{YEAR}`

**Example:** `46374500000194-1-006949/2025`

| Component | Value | Description |
|-----------|-------|-------------|
| CNPJ | `46374500000194` | Organization identifier |
| Digit | `1` | Always "1" for tenders (contratações) |
| Sequential | `006949` | Sequential number (with leading zeros) |
| Year | `2025` | Tender year |

---

### Where to Find Control Numbers

#### 1. From Your Database

```sql
-- Get control number directly
SELECT control_number FROM tenders WHERE id = 12345;

-- Or construct it from components
SELECT
  cnpj || '-1-' || LPAD(sequential_number::text, 6, '0') || '/' || year AS control_number
FROM tenders
WHERE id = 12345;
```

#### 2. From PNCP Website URL

```
https://pncp.gov.br/app/editais/46374500000194-1-006949-2025
```
Control number: `46374500000194-1-006949/2025` (replace last `-` with `/`)

#### 3. From PNCP Search Results

When browsing tenders on PNCP, the control number appears in the tender details.

## Integration with Database

### Fetch Documents for Tenders in Database

```python
import asyncio
from scripts.fetch_tender_documents import TenderDocumentFetcher, parse_control_number
from database import create_db_manager_from_env

async def fetch_documents_for_recent_tenders():
    """Fetch documents for recent tenders in database"""
    db = create_db_manager_from_env()
    fetcher = TenderDocumentFetcher(output_dir="tender_documents")

    try:
        conn = await db.get_connection()

        # Method 1: Using control_number field (if available)
        tenders = await conn.fetch("""
            SELECT control_number
            FROM tenders
            WHERE publication_date >= CURRENT_DATE - INTERVAL '7 days'
            LIMIT 100
        """)

        for tender in tenders:
            control_num = tender['control_number']
            print(f"Fetching documents for {control_num}")

            # Parse control number
            cnpj, year, sequential = parse_control_number(control_num)

            await fetcher.fetch_all(cnpj, year, sequential, download=True)

        # Method 2: Using individual fields
        tenders = await conn.fetch("""
            SELECT cnpj, year, sequential_number
            FROM tenders
            WHERE publication_date >= CURRENT_DATE - INTERVAL '7 days'
            LIMIT 100
        """)

        for tender in tenders:
            print(f"Fetching documents for {tender['cnpj']}/{tender['year']}/{tender['sequential_number']}")

            await fetcher.fetch_all(
                tender['cnpj'],
                tender['year'],
                tender['sequential_number'],
                download=True
            )

    finally:
        await fetcher.close()
        await db.close()

asyncio.run(fetch_documents_for_recent_tenders())
```

## Error Handling

The script handles common errors gracefully:

- **404 Not Found:** Tender or documents don't exist
- **204 No Content:** No documents/atas available
- **Rate Limiting:** Automatic retry with backoff
- **Network Errors:** Logged with error details

## Batch Processing

### Using Control Numbers (Recommended)

```bash
# Create a list of control numbers
cat > control_numbers.txt << EOF
46374500000194-1-006949/2025
46374500000194-1-006950/2025
46374500000194-1-006951/2025
EOF

# Process each tender
while read -r control_num; do
    echo "Processing $control_num"
    python3 scripts/fetch_tender_documents.py \
        --control-number "$control_num" \
        --download
    sleep 2  # Rate limiting
done < control_numbers.txt
```

### Using Individual Components

```bash
# Create a list of tenders (CSV format)
cat > tenders.txt << EOF
46374500000194,2025,6949
46374500000194,2025,6950
46374500000194,2025,6951
EOF

# Process each tender
while IFS=',' read -r cnpj year seq; do
    echo "Processing $cnpj/$year/$seq"
    python3 scripts/fetch_tender_documents.py \
        --cnpj "$cnpj" \
        --year "$year" \
        --sequential "$seq" \
        --download
    sleep 2  # Rate limiting
done < tenders.txt
```

## Performance Notes

- **Documents:** Fast (usually 1-2 seconds per tender)
- **Downloads:** Depends on file size (typically 100KB-5MB PDFs)
- **Rate Limiting:** Built-in to respect PNCP API limits
- **Concurrent:** Can run multiple instances for different states

## Troubleshooting

### "No documents found"

- Some tenders may not have uploaded documents yet
- Check if tender exists: `control_number` on PNCP website

### "Session error"

- The script automatically manages HTTP sessions
- If issues persist, restart the script

### "Download failed"

- Some documents may be temporarily unavailable
- Retry the same command - it will skip already downloaded files

## Related Scripts

- `main.py` - Main processing pipeline
- `scripts/batch/run_monthly_batches.py` - Batch tender discovery
- `scripts/debug/check_db_stats.py` - Database statistics

## Support

For issues or questions:
1. Check logs in terminal output
2. Verify tender exists on PNCP website
3. Review `metadata.json` for API responses

---

**Created:** 2025-10-14
**Version:** 1.0
**API:** PNCP Consultation API v1
