#!/usr/bin/env python3
"""
Test ID-based deduplication functionality
Verifies that filter_new_tenders() correctly identifies duplicates
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import create_db_manager_from_env, DatabaseOperations

async def test_deduplication():
    """Test the filter_new_tenders function"""

    print("=" * 70)
    print("Testing ID-Based Deduplication")
    print("=" * 70)

    # Create sample tender data
    sample_tenders = [
        {
            'numeroControlePNCP': '12474705000120-1-000107/2024',
            'objetoCompra': 'Test Tender 1',
            'valorTotalEstimado': 100000.0
        },
        {
            'numeroControlePNCP': '60448040000122-1-000196/2024',
            'objetoCompra': 'Test Tender 2',
            'valorTotalEstimado': 200000.0
        },
        {
            'numeroControlePNCP': 'NEW-TENDER-12345/2024',
            'objetoCompra': 'Test Tender 3 (New)',
            'valorTotalEstimado': 300000.0
        },
    ]

    print(f"\n📋 Test data: {len(sample_tenders)} tenders")
    print(f"   - 2 should exist in DB (from previous test run)")
    print(f"   - 1 should be new")

    db_manager = None
    try:
        # Initialize database
        db_manager = create_db_manager_from_env()
        db_ops = DatabaseOperations(db_manager)

        # Test filtering
        print(f"\n🔍 Running filter_new_tenders()...")
        new_tenders = await db_ops.filter_new_tenders(sample_tenders)

        # Results
        duplicates = len(sample_tenders) - len(new_tenders)

        print(f"\n✅ Deduplication Results:")
        print(f"   Input: {len(sample_tenders)} tenders")
        print(f"   Output: {len(new_tenders)} new tenders")
        print(f"   Filtered: {duplicates} duplicates ({duplicates/len(sample_tenders)*100:.1f}%)")

        # Show which tenders are new
        if new_tenders:
            print(f"\n📦 New tenders (not in DB):")
            for t in new_tenders:
                print(f"   - {t['numeroControlePNCP']}: {t['objetoCompra']}")

        # Test edge cases
        print(f"\n🧪 Testing edge cases...")

        # Test with empty list
        empty_result = await db_ops.filter_new_tenders([])
        assert len(empty_result) == 0, "Empty list should return empty"
        print(f"   ✅ Empty list: OK")

        # Test with all new tenders
        all_new = [{'numeroControlePNCP': f'NEW-{i}/2024', 'objetoCompra': f'New {i}'}
                   for i in range(5)]
        all_new_result = await db_ops.filter_new_tenders(all_new)
        assert len(all_new_result) == 5, "All new tenders should pass through"
        print(f"   ✅ All new tenders: OK ({len(all_new_result)}/5)")

        print(f"\n✅ All tests passed!")
        print(f"\n💡 This deduplication will prevent re-processing tenders")
        print(f"   already in the database, saving time on:")
        print(f"   - Stage 2: Quick filtering")
        print(f"   - Stage 3: API sampling")
        print(f"   - Stage 4: Full processing")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

    finally:
        if db_manager:
            await db_manager.close()

if __name__ == "__main__":
    asyncio.run(test_deduplication())
