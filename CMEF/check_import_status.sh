#!/bin/bash
# Quick status check for database import

echo "📊 Database Import Status"
echo "=========================="
echo ""

# Check if process is running
if ps aux | grep -v grep | grep auto_setup_unified_db.py > /dev/null; then
    echo "✅ Import process is running"
    echo ""

    # Show last few log lines
    echo "📝 Recent progress:"
    tail -10 /Users/gabrielreginatto/Desktop/Code/Medical/CMEF/logs/auto_unified_setup_fixed.log | grep -E "(Progress:|✅|STEP|COMPLETED)"
else
    echo "⚠️  Import process not found (may have completed or failed)"
    echo ""

    # Check for completion or error
    if grep -q "SETUP COMPLETED SUCCESSFULLY" /Users/gabrielreginatto/Desktop/Code/Medical/CMEF/logs/auto_unified_setup_fixed.log 2>/dev/null; then
        echo "✅ Import completed successfully!"
        echo ""
        echo "📊 Final summary:"
        tail -30 /Users/gabrielreginatto/Desktop/Code/Medical/CMEF/logs/auto_unified_setup_fixed.log | grep -A 20 "DATABASE SUMMARY"
    elif grep -q "Setup failed" /Users/gabrielreginatto/Desktop/Code/Medical/CMEF/logs/auto_unified_setup_fixed.log 2>/dev/null; then
        echo "❌ Import failed - check logs for details"
        tail -20 /Users/gabrielreginatto/Desktop/Code/Medical/CMEF/logs/auto_unified_setup_fixed.log
    else
        echo "📄 Last log entries:"
        tail -15 /Users/gabrielreginatto/Desktop/Code/Medical/CMEF/logs/auto_unified_setup_fixed.log
    fi
fi

echo ""
echo "💡 To view live progress: tail -f CMEF/logs/auto_unified_setup_fixed.log"
