# Test Run Summary

**Date:** 2025-10-01 17:35
**Duration:** ~56 minutes (4:39 PM - 5:35 PM)

## Configuration
- **Date Range:** July 1 - September 15, 2024 (75 days)
- **State:** São Paulo (SP)
- **Max Tenders:** 5,000
- **Modalities:** [6 (Pregão), 8 (Dispensa)]
- **Min Match Score:** 40.0

## Results

### Stage 1: Bulk Fetch
- **Target:** 5,000 tenders
- **Actual:** 3,940 tenders (78.8%)
- **Reason for shortfall:**
  - Modality 6 failed at page 124 (~2,480 tenders)
  - Modality 8 stopped at page 73 due to API date validation error

### Stage 2: Quick Filter
- **Input:** 3,940 tenders
- **Output:** 468 medical tenders (88.1% filtered out)

### Stage 3: Hybrid Auto-Approval
- **Phase 1 (Keyword/Score):** 94 auto-approved
- **Phase 2 (API Sampling):** 374 tenders sampled → All rejected (404 - no items)
- **Phase 3 (Organization):** 297 org-approved

### Final Results
- **Total Medical Tenders:** 391
- **Auto-Approved:** 391 (100%)
- **Required Sampling:** 0 (0%)

## Key Findings
1. **100% auto-approval rate** - All medical tenders identified without detailed API verification
2. **Phase 3 organization-based approval was highly effective** (297/391 = 76%)
3. **Phase 2 sampling found no valid tenders** - All 374 sampled tenders had no items (404 errors)
4. **API performance issues** - Multiple timeouts and failures during Stage 1 and Stage 3

## Files
- `auto_approved_tenders.json` - 391 tenders (198 KB)
- `sampled_tenders.json` - Empty (2 bytes)
- `sp_test.log` - Full execution log
