---
description: Run PNCP batch processing for a state (Jan 2024 - Jul 2025, 19 months)
argument-hint: [STATE_CODE]
---

Run batch processing for state $ARGUMENTS using this command:

python3 scripts/batch/run_monthly_batches.py --state $ARGUMENTS --start 2024-01 --months 19

This processes 19 months of tender data (January 2024 through July 2025) for the specified Brazilian state.
