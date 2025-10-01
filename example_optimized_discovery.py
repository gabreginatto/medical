"""
Example Usage: Optimized Multi-Stage Tender Discovery
Demonstrates the complete workflow with all 4 stages and analytics
"""

import asyncio
import logging
from datetime import datetime, timedelta

from config import ProcessingConfig
from pncp_api import PNCPAPIClient
from classifier import TenderClassifier
from database import CloudSQLManager, DatabaseOperations, create_db_manager_from_env
from optimized_discovery import OptimizedTenderDiscovery, print_metrics_summary
from analytics import MedicalProcurementAnalytics, print_analytics_report
from org_cache import get_org_cache, print_cache_statistics

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def example_1_single_state_optimized():
    """Example 1: Discover medical tenders for a single state (São Paulo)"""

    print("\n" + "="*70)
    print("EXAMPLE 1: Single State Discovery (São Paulo - Last 30 Days)")
    print("="*70 + "\n")

    # Configuration for São Paulo
    config = ProcessingConfig(
        enabled_states=['SP'],
        min_tender_value=10_000.0,
        max_tender_value=5_000_000.0,
        allowed_modalities=[6, 8],  # Pregão Eletrônico, Dispensa
        min_match_score=40.0,
        use_org_cache=True,
        catmat_boost_enabled=True
    )

    # Date range: last 30 days
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    start_date_str = start_date.strftime('%Y%m%d')
    end_date_str = end_date.strftime('%Y%m%d')

    # Initialize components
    api_client = PNCPAPIClient()
    await api_client.start_session()

    classifier = TenderClassifier()
    db_manager = create_db_manager_from_env()
    db_ops = DatabaseOperations(db_manager)

    # Create optimized discovery engine
    discovery_engine = OptimizedTenderDiscovery(
        api_client, classifier, db_ops, config
    )

    try:
        # Run optimized discovery
        logger.info("Starting optimized discovery...")
        medical_tenders, metrics = await discovery_engine.discover_medical_tenders_optimized(
            'SP', start_date_str, end_date_str
        )

        # Print results
        print(f"\n✅ Discovery Complete!")
        print(f"Found {len(medical_tenders)} medical tenders\n")

        # Print detailed metrics
        print_metrics_summary(metrics)

        # Print sample tenders
        if medical_tenders:
            print("\n--- Sample Medical Tenders (Top 5) ---")
            for i, tender in enumerate(medical_tenders[:5], 1):
                org_name = tender.get('orgaoEntidade', {}).get('razaoSocial', 'N/A')
                value = tender.get('valorTotalHomologado', 0)
                score = tender.get('medical_confidence', 0)
                print(f"\n{i}. {org_name}")
                print(f"   Value: R${value:,.2f}")
                print(f"   Confidence: {score:.1f}%")
                print(f"   Control: {tender.get('numeroControlePNCPCompra', 'N/A')}")

        # Performance summary
        summary = discovery_engine.get_performance_summary()
        print(f"\n📊 API Efficiency: {summary['api_efficiency_ratio']:.4f} (tenders/API call)")
        print(f"⏱️  Total Duration: {summary['total_duration_seconds']:.2f}s")

    finally:
        await api_client.close_session()


async def example_2_multiple_states_parallel():
    """Example 2: Process multiple states in parallel"""

    print("\n" + "="*70)
    print("EXAMPLE 2: Multi-State Discovery (SP, RJ, MG - Last 14 Days)")
    print("="*70 + "\n")

    # Configuration
    config = ProcessingConfig(
        enabled_states=['SP', 'RJ', 'MG'],
        min_tender_value=50_000.0,  # Focus on larger tenders
        allowed_modalities=[6],  # Pregão Eletrônico only
        min_match_score=60.0,
        use_org_cache=True
    )

    # Date range: last 14 days
    end_date = datetime.now()
    start_date = end_date - timedelta(days=14)
    start_date_str = start_date.strftime('%Y%m%d')
    end_date_str = end_date.strftime('%Y%m%d')

    # Initialize
    api_client = PNCPAPIClient()
    await api_client.start_session()

    classifier = TenderClassifier()
    db_manager = create_db_manager_from_env()
    db_ops = DatabaseOperations(db_manager)

    try:
        # Process states in parallel
        async def process_state(state_code):
            engine = OptimizedTenderDiscovery(api_client, classifier, db_ops, config)
            return await engine.discover_medical_tenders_optimized(
                state_code, start_date_str, end_date_str
            )

        # Run in parallel
        logger.info("Processing multiple states in parallel...")
        results = await asyncio.gather(
            process_state('SP'),
            process_state('RJ'),
            process_state('MG')
        )

        # Aggregate results
        total_tenders = sum(len(tenders) for tenders, _ in results)
        print(f"\n✅ Multi-State Discovery Complete!")
        print(f"Total Medical Tenders Found: {total_tenders}")

        for state, (tenders, metrics) in zip(['SP', 'RJ', 'MG'], results):
            print(f"\n{state}: {len(tenders)} tenders")
            print(f"  API Calls: {metrics.total_api_calls}")
            print(f"  Duration: {metrics.total_duration:.2f}s")

    finally:
        await api_client.close_session()


async def example_3_high_value_with_catmat():
    """Example 3: Find high-value tenders with CATMAT codes"""

    print("\n" + "="*70)
    print("EXAMPLE 3: High-Value CATMAT Tenders (SP - Last 60 Days)")
    print("="*70 + "\n")

    # Configuration for high-value medical equipment
    config = ProcessingConfig(
        enabled_states=['SP'],
        min_tender_value=100_000.0,  # High value only
        max_tender_value=10_000_000.0,
        allowed_modalities=[6, 4],  # Pregão and Concorrência
        min_match_score=70.0,
        require_medical_catmat=True,  # MUST have CATMAT codes
        use_org_cache=True
    )

    # Date range: last 60 days
    end_date = datetime.now()
    start_date = end_date - timedelta(days=60)
    start_date_str = start_date.strftime('%Y%m%d')
    end_date_str = end_date.strftime('%Y%m%d')

    # Initialize
    api_client = PNCPAPIClient()
    await api_client.start_session()

    classifier = TenderClassifier()
    db_manager = create_db_manager_from_env()
    db_ops = DatabaseOperations(db_manager)

    discovery_engine = OptimizedTenderDiscovery(
        api_client, classifier, db_ops, config
    )

    try:
        medical_tenders, metrics = await discovery_engine.discover_medical_tenders_optimized(
            'SP', start_date_str, end_date_str
        )

        print(f"\n✅ High-Value CATMAT Discovery Complete!")
        print(f"Found {len(medical_tenders)} high-value medical equipment tenders\n")

        # Show tenders with CATMAT codes
        if medical_tenders:
            print("--- High-Value Tenders with CATMAT Codes ---")
            for tender in medical_tenders[:10]:
                org_name = tender.get('orgaoEntidade', {}).get('razaoSocial', 'N/A')
                value = tender.get('valorTotalHomologado', 0)
                catmat_codes = tender.get('catmat_codes', [])

                print(f"\n• {org_name}")
                print(f"  Value: R${value:,.2f}")
                if catmat_codes:
                    print(f"  CATMAT Codes: {', '.join(catmat_codes)}")

        print_metrics_summary(metrics)

    finally:
        await api_client.close_session()


async def example_4_with_analytics():
    """Example 4: Full workflow with analytics report"""

    print("\n" + "="*70)
    print("EXAMPLE 4: Discovery + Analytics Report (RJ - Last 30 Days)")
    print("="*70 + "\n")

    # Configuration
    config = ProcessingConfig(
        enabled_states=['RJ'],
        min_tender_value=5_000.0,
        allowed_modalities=[6, 8],
        min_match_score=50.0,
        use_org_cache=True
    )

    # Date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    start_date_str = start_date.strftime('%Y%m%d')
    end_date_str = end_date.strftime('%Y%m%d')

    # Initialize
    api_client = PNCPAPIClient()
    await api_client.start_session()

    classifier = TenderClassifier()
    db_manager = create_db_manager_from_env()
    db_ops = DatabaseOperations(db_manager)

    discovery_engine = OptimizedTenderDiscovery(
        api_client, classifier, db_ops, config
    )

    try:
        # Step 1: Discover tenders
        logger.info("Step 1: Running optimized discovery...")
        medical_tenders, metrics = await discovery_engine.discover_medical_tenders_optimized(
            'RJ', start_date_str, end_date_str
        )

        print(f"\n✅ Discovered {len(medical_tenders)} medical tenders")
        print_metrics_summary(metrics)

        # Step 2: Generate analytics
        logger.info("Step 2: Generating analytics report...")
        analytics = MedicalProcurementAnalytics(db_ops)
        report = await analytics.generate_comprehensive_report(state_code='RJ')

        # Print analytics
        print_analytics_report(report)

        # Export to JSON
        analytics.export_report_to_json(report, 'analytics_report_RJ.json')
        print("📄 Analytics report exported to analytics_report_RJ.json")

    finally:
        await api_client.close_session()


async def example_5_cache_warming():
    """Example 5: Pre-warm organization cache with known medical orgs"""

    print("\n" + "="*70)
    print("EXAMPLE 5: Organization Cache Warming")
    print("="*70 + "\n")

    # Get org cache
    org_cache = get_org_cache()

    # Print current cache stats
    print("Current Cache Statistics:")
    print_cache_statistics(org_cache)

    # Add known medical organizations manually (seed data)
    from config import OrganizationType, GovernmentLevel

    known_orgs = [
        {
            'cnpj': '46.374.500/0001-19',
            'name': 'Hospital das Clínicas - Faculdade de Medicina USP',
            'org_type': OrganizationType.HOSPITAL,
            'gov_level': GovernmentLevel.STATE,
            'state': 'SP',
            'confidence': 98.0
        },
        {
            'cnpj': '60.742.616/0001-60',
            'name': 'Hospital Israelita Albert Einstein',
            'org_type': OrganizationType.HOSPITAL,
            'gov_level': GovernmentLevel.MUNICIPAL,
            'state': 'SP',
            'confidence': 95.0
        },
        {
            'cnpj': '42.498.717/0001-48',
            'name': 'Hospital Universitário Clementino Fraga Filho',
            'org_type': OrganizationType.HOSPITAL,
            'gov_level': GovernmentLevel.FEDERAL,
            'state': 'RJ',
            'confidence': 97.0
        }
    ]

    print("\n🔥 Warming cache with known medical organizations...")
    for org in known_orgs:
        org_cache.add_medical_organization(
            org['cnpj'], org['name'], org['org_type'],
            org['gov_level'], org['state'], org['confidence']
        )
        print(f"✓ Added: {org['name']} ({org['cnpj']})")

    # Save cache
    org_cache.save_cache()
    print("\n💾 Cache saved successfully!")

    # Print updated stats
    print("\nUpdated Cache Statistics:")
    print_cache_statistics(org_cache)


async def main():
    """Run all examples"""

    print("\n" + "="*70)
    print("🚀 OPTIMIZED TENDER DISCOVERY - EXAMPLES")
    print("="*70)

    # Menu
    print("\nAvailable Examples:")
    print("1. Single State Discovery (SP)")
    print("2. Multi-State Parallel Discovery (SP, RJ, MG)")
    print("3. High-Value CATMAT Tenders (SP)")
    print("4. Discovery + Analytics Report (RJ)")
    print("5. Cache Warming (add known medical orgs)")
    print("6. Run All Examples (sequential)")

    choice = input("\nSelect example (1-6): ").strip()

    if choice == '1':
        await example_1_single_state_optimized()
    elif choice == '2':
        await example_2_multiple_states_parallel()
    elif choice == '3':
        await example_3_high_value_with_catmat()
    elif choice == '4':
        await example_4_with_analytics()
    elif choice == '5':
        await example_5_cache_warming()
    elif choice == '6':
        print("\n🔄 Running all examples sequentially...\n")
        await example_5_cache_warming()  # Warm cache first
        await example_1_single_state_optimized()
        await example_2_multiple_states_parallel()
        await example_3_high_value_with_catmat()
        await example_4_with_analytics()
    else:
        print("Invalid choice. Please run again and select 1-6.")

    print("\n" + "="*70)
    print("✅ EXAMPLES COMPLETE")
    print("="*70 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
