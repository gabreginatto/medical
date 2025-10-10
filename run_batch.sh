#!/bin/bash
# Quick wrapper for batch processing
# Usage: ./run_batch.sh SP (for São Paulo)
#        ./run_batch.sh RJ (for Rio de Janeiro)
#        etc.

if [ -z "$1" ]; then
    echo "❌ Error: Please provide a state code"
    echo ""
    echo "Usage: ./run_batch.sh <STATE_CODE>"
    echo ""
    echo "Examples:"
    echo "  ./run_batch.sh SP    # São Paulo"
    echo "  ./run_batch.sh RJ    # Rio de Janeiro"
    echo "  ./run_batch.sh MG    # Minas Gerais"
    echo "  ./run_batch.sh SC    # Santa Catarina"
    echo "  ./run_batch.sh RS    # Rio Grande do Sul"
    echo "  ./run_batch.sh PR    # Paraná"
    echo "  ./run_batch.sh BA    # Bahia"
    echo ""
    exit 1
fi

STATE=$(echo "$1" | tr '[:lower:]' '[:upper:]')

echo "🚀 Starting batch processing for state: $STATE"
echo "📅 Date range: January 2024 - July 2025 (19 months)"
echo ""

python3 scripts/batch/run_monthly_batches.py --state "$STATE" --start 2024-01 --months 19
