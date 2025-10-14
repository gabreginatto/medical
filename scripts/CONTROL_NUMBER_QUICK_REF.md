# Control Number Quick Reference

## What is a Control Number?

The **control number** is the unique identifier for tenders in the PNCP system.

**Format:** `{CNPJ}-1-{SEQUENTIAL}/{YEAR}`

**Example:** `46374500000194-1-006949/2025`

---

## Quick Commands

### Fetch Everything (Edital + History + Atas)

```bash
python3 scripts/fetch_tender_documents.py \
  --control-number "46374500000194-1-006949/2025"
```

### Download All Documents

```bash
python3 scripts/fetch_tender_documents.py \
  --control "46374500000194-1-006949/2025" \
  --download
```

### Fetch Only Edital

```bash
python3 scripts/fetch_tender_documents.py \
  --control "46374500000194-1-006949/2025" \
  --documents-only
```

---

## Where to Find Control Numbers

| Source | Format | Example |
|--------|--------|---------|
| **Database** | `control_number` field | `46374500000194-1-006949/2025` |
| **PNCP URL** | Replace last `-` with `/` | `...46374500000194-1-006949-2025` → `46374500000194-1-006949/2025` |
| **PNCP Portal** | Listed in tender details | `46374500000194-1-006949/2025` |

---

## From Your Database

```sql
-- Get control number directly
SELECT control_number FROM tenders WHERE id = 12345;

-- Construct from components
SELECT
  cnpj || '-1-' || LPAD(sequential_number::text, 6, '0') || '/' || year
FROM tenders
WHERE id = 12345;
```

---

## Parse Control Number in Python

```python
from scripts.fetch_tender_documents import parse_control_number

control_num = "46374500000194-1-006949/2025"
cnpj, year, sequential = parse_control_number(control_num)

print(f"CNPJ: {cnpj}")          # 46374500000194
print(f"Year: {year}")           # 2025
print(f"Sequential: {sequential}") # 6949
```

---

## Batch Processing

```bash
# Create list
cat > tenders.txt << EOF
46374500000194-1-006949/2025
46374500000194-1-006950/2025
46374500000194-1-006951/2025
EOF

# Process all
while read control_num; do
    python3 scripts/fetch_tender_documents.py --control "$control_num" --download
    sleep 2
done < tenders.txt
```

---

## Control Number Components

| Part | Value | Description |
|------|-------|-------------|
| **CNPJ** | `46374500000194` | Organization identifier (14 digits) |
| **Digit** | `1` | Fixed digit for tenders (always "1") |
| **Sequential** | `006949` | Tender sequential number (6 digits with leading zeros) |
| **Year** | `2025` | Tender year (4 digits) |

---

## Common Patterns

### PNCP URL → Control Number

```
URL:     https://pncp.gov.br/app/editais/46374500000194-1-006949-2025
Control: 46374500000194-1-006949/2025
                                      ↑
                              Replace - with /
```

### Database → Control Number

```sql
-- If you only have individual fields
SELECT
  CONCAT(
    cnpj,
    '-1-',
    LPAD(sequential_number::text, 6, '0'),
    '/',
    year
  ) as control_number
FROM tenders;
```

---

## Troubleshooting

### Invalid format error

```bash
❌ Error: Invalid control number format: 46374500000194-006949/2025

✅ Correct: 46374500000194-1-006949/2025
                            ↑
                     Must include -1-
```

### Missing leading zeros

```bash
❌ Wrong: 46374500000194-1-6949/2025

✅ Right: 46374500000194-1-006949/2025
                            ↑↑
                     6 digits with zeros
```

---

**Updated:** 2025-10-14
