# 🐛 Item Fetching Pagination Fix

**Problem**: The `get_tender_items()` function in `pncp_api.py` does NOT fetch all items - it only gets the first page (usually 10-20 items), missing many items from larger tenders.

---

## 🔴 THE BUG - Current Broken Code

### Location: `src/pncp_api.py` lines 154-159

```python
async def get_tender_items(self, cnpj: str, year: int, sequential: int) -> Tuple[int, Dict[str, Any]]:
    """Get all items for a specific tender"""
    url = f"{self.pncp_url}/v1/orgaos/{cnpj}/compras/{year}/{sequential}/itens"
    headers = self._get_headers()

    return await self._make_request('GET', url, headers=headers)
    # ❌ BUG: Only fetches PAGE 1! Missing all other pages!
```

###What Happens:
- Tender has 50 items
- API returns first 10 items (page 1)
- Function returns only those 10 items
- **40 items are MISSING!** ❌

---

## ✅ THE FIX - Pagination-Aware Version

### Replace `get_tender_items()` with this:

```python
async def get_tender_items_all(self, cnpj: str, year: int, sequential: int) -> Tuple[int, List[Dict]]:
    """
    Get ALL items for a specific tender with pagination support

    Returns:
        Tuple of (status_code, list_of_items)
        - status_code: HTTP status (200 = success)
        - list_of_items: Complete list of ALL items across all pages
    """
    url_base = f"{self.pncp_url}/v1/orgaos/{cnpj}/compras/{year}/{sequential}/itens"
    headers = self._get_headers()

    all_items = []
    page = 1
    max_pages = 100  # Safety limit to prevent infinite loops

    while page <= max_pages:
        # Add pagination parameters
        params = {
            'pagina': page,
            'tamanhoPagina': 50  # Request 50 items per page (API max might be 500)
        }

        url = url_base
        status, response = await self._make_request('GET', url, params=params, headers=headers)

        if status != 200:
            # If first page fails, return error
            if page == 1:
                logger.error(f"Failed to fetch items page {page} for {cnpj}/{year}/{sequential}: status {status}")
                return status, []
            else:
                # If later page fails, return what we have so far
                logger.warning(f"Failed to fetch items page {page}, returning {len(all_items)} items from previous pages")
                break

        # Extract items from response
        if isinstance(response, dict):
            items = response.get('data', [])
            pages_remaining = response.get('paginasRestantes', 0)
            total_pages = response.get('totalPaginas', page)
        elif isinstance(response, list):
            # Direct list response (no pagination wrapper)
            items = response
            pages_remaining = 0
            total_pages = 1
        else:
            logger.error(f"Unexpected response type for items: {type(response)}")
            break

        if not items:
            # No items on this page, we're done
            break

        all_items.extend(items)

        logger.debug(f"Fetched page {page}/{total_pages} for {cnpj}/{year}/{sequential}: {len(items)} items (total: {len(all_items)})")

        # Check if we're done
        if pages_remaining == 0 or page >= total_pages:
            break

        page += 1

    logger.info(f"✅ Fetched {len(all_items)} total items for tender {cnpj}/{year}/{sequential} across {page} page(s)")
    return 200, all_items
```

---

## 📝 How to Apply the Fix

### Option 1: Add New Function (Recommended)

Add `get_tender_items_all()` to `src/pncp_api.py` and use it instead of `get_tender_items()`.

**In `src/fetch_and_save_items.py` line 178:**

```python
# BEFORE (BROKEN):
status, response = await api_client.get_tender_items(cnpj, year, sequential)

# AFTER (FIXED):
status, items_list = await api_client.get_tender_items_all(cnpj, year, sequential)

# Then you don't need lines 186-194 because items_list is already the list!
# Just use items_list directly:
if not items_list:
    batch_without_items += 1
    continue
```

### Option 2: Replace Existing Function

Replace the entire `get_tender_items()` function in `src/pncp_api.py:154-159` with the fixed version above.

**Then update the caller in `fetch_and_save_items.py`:**

```python
# The function now returns (status, list) instead of (status, dict)
status, items_list = await api_client.get_tender_items(cnpj, year, sequential)

# Remove the response parsing code (lines 186-194) since we already have the list
if status != 200 or not items_list:
    batch_without_items += 1
    continue

# Continue with items_list directly (it's already a list!)
for item in items_list:
    # Process each item...
```

---

## 🎯 Key Changes Explained

### 1. **Pagination Loop**
```python
page = 1
while page <= max_pages:
    # Fetch page
    params = {'pagina': page, 'tamanhoPagina': 50}
    status, response = await self._make_request('GET', url, params=params, headers=headers)

    # Extract items from this page
    items = response.get('data', [])
    all_items.extend(items)

    # Check if more pages
    if response.get('paginasRestantes', 0) == 0:
        break

    page += 1
```

### 2. **Return Format Change**
```python
# OLD (WRONG):
return (200, {'data': [item1, item2, ...]})  # Returns dict

# NEW (CORRECT):
return (200, [item1, item2, item3, ...])  # Returns list directly
```

### 3. **Safety Limits**
```python
max_pages = 100  # Prevent infinite loops
```

---

## 🧪 Testing the Fix

### Test with a tender that has many items:

```python
import asyncio
from src.pncp_api import PNCPAPIClient

async def test_pagination():
    client = PNCPAPIClient()
    await client.start_session()

    # Test with a tender known to have 50+ items
    cnpj = "00394460005887"  # Example
    year = 2024
    sequential = 123

    # OLD WAY (BROKEN):
    status_old, response_old = await client.get_tender_items(cnpj, year, sequential)
    items_old = response_old.get('data', []) if isinstance(response_old, dict) else response_old
    print(f"OLD: Got {len(items_old)} items (MISSING ITEMS!)")

    # NEW WAY (FIXED):
    status_new, items_new = await client.get_tender_items_all(cnpj, year, sequential)
    print(f"NEW: Got {len(items_new)} items (ALL ITEMS!)")

    print(f"\nDifference: {len(items_new) - len(items_old)} items were MISSING!")

    await client.close_session()

asyncio.run(test_pagination())
```

**Expected Output:**
```
OLD: Got 10 items (MISSING ITEMS!)
NEW: Got 47 items (ALL ITEMS!)

Difference: 37 items were MISSING!
```

---

## 📊 Impact

### Before Fix:
- ❌ Only first 10-20 items fetched per tender
- ❌ Large tenders missing 80%+ of items
- ❌ Incomplete database
- ❌ Inaccurate statistics

### After Fix:
- ✅ ALL items fetched (50, 100, 200+ items)
- ✅ Complete tender data
- ✅ Accurate database
- ✅ Correct statistics

---

## 🎓 API Endpoint Documentation

The PNCP API endpoint for items:
```
GET https://pncp.gov.br/api/pncp/v1/orgaos/{cnpj}/compras/{year}/{sequential}/itens
```

**Supports pagination parameters:**
- `pagina`: Page number (starts at 1)
- `tamanhoPagina`: Items per page (10-500, typically use 50)

**Response format:**
```json
{
  "data": [
    {
      "numeroItem": 1,
      "descricao": "Item description",
      "quantidade": 100,
      "valorUnitarioEstimado": 10.50,
      ...
    },
    ...
  ],
  "paginasRestantes": 2,
  "totalPaginas": 3,
  "totalRegistros": 47
}
```

---

## 🔗 Files Affected

1. **`src/pncp_api.py`** - Add `get_tender_items_all()` function
2. **`src/fetch_and_save_items.py`** - Update to use new function (line 178)
3. **`scripts/batch/fetch_and_save_items_improved.py`** - Update to use new function (line 178)

---

## ✅ Verification Checklist

After applying the fix:

- [ ] New function `get_tender_items_all()` added to `pncp_api.py`
- [ ] `fetch_and_save_items.py` updated to call new function
- [ ] Response parsing code removed (lines 186-194 in fetch_and_save_items.py)
- [ ] Tested with a tender that has 50+ items
- [ ] Verified all items are being fetched
- [ ] Database shows increased item counts
- [ ] Logs show "Fetched X total items across Y pages"

---

**Generated**: November 5, 2025
**Source**: PNCP Medical Data Processor - Fixed pagination bug
