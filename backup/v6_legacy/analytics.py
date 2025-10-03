"""
Analytics Module for Medical Procurement Insights
Provides performance tracking, medical equipment analysis, and procurement trends
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import json

from database import DatabaseOperations

logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetrics:
    """Performance metrics for discovery operations"""
    operation_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    tenders_processed: int = 0
    api_calls: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    errors: int = 0

    @property
    def duration_seconds(self) -> float:
        """Calculate duration in seconds"""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0

    @property
    def throughput(self) -> float:
        """Tenders processed per second"""
        duration = self.duration_seconds
        if duration > 0:
            return self.tenders_processed / duration
        return 0.0

    @property
    def cache_hit_rate(self) -> float:
        """Cache hit rate percentage"""
        total = self.cache_hits + self.cache_misses
        if total > 0:
            return (self.cache_hits / total) * 100
        return 0.0

    @property
    def api_efficiency(self) -> float:
        """Tenders per API call ratio"""
        if self.api_calls > 0:
            return self.tenders_processed / self.api_calls
        return 0.0


class PerformanceTracker:
    """Track performance metrics across discovery operations"""

    def __init__(self):
        self.metrics: List[PerformanceMetrics] = []
        self.current_operation: Optional[PerformanceMetrics] = None

    def start_operation(self, operation_name: str) -> PerformanceMetrics:
        """Start tracking a new operation"""
        metric = PerformanceMetrics(
            operation_name=operation_name,
            start_time=datetime.now()
        )
        self.current_operation = metric
        self.metrics.append(metric)
        return metric

    def end_operation(self):
        """End the current operation"""
        if self.current_operation:
            self.current_operation.end_time = datetime.now()
            self.current_operation = None

    def record_api_call(self):
        """Record an API call"""
        if self.current_operation:
            self.current_operation.api_calls += 1

    def record_cache_hit(self):
        """Record a cache hit"""
        if self.current_operation:
            self.current_operation.cache_hits += 1

    def record_cache_miss(self):
        """Record a cache miss"""
        if self.current_operation:
            self.current_operation.cache_misses += 1

    def record_tender_processed(self, count: int = 1):
        """Record tenders processed"""
        if self.current_operation:
            self.current_operation.tenders_processed += count

    def record_error(self):
        """Record an error"""
        if self.current_operation:
            self.current_operation.errors += 1

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of all operations"""
        if not self.metrics:
            return {}

        total_tenders = sum(m.tenders_processed for m in self.metrics)
        total_api_calls = sum(m.api_calls for m in self.metrics)
        total_duration = sum(m.duration_seconds for m in self.metrics)
        total_errors = sum(m.errors for m in self.metrics)

        return {
            'total_operations': len(self.metrics),
            'total_tenders_processed': total_tenders,
            'total_api_calls': total_api_calls,
            'total_duration_seconds': total_duration,
            'total_errors': total_errors,
            'average_throughput': total_tenders / total_duration if total_duration > 0 else 0,
            'api_efficiency': total_tenders / total_api_calls if total_api_calls > 0 else 0,
            'operations': [
                {
                    'name': m.operation_name,
                    'duration': m.duration_seconds,
                    'tenders': m.tenders_processed,
                    'api_calls': m.api_calls,
                    'throughput': m.throughput,
                    'errors': m.errors
                }
                for m in self.metrics
            ]
        }


class MedicalProcurementAnalytics:
    """Analytics for medical procurement insights"""

    def __init__(self, db_operations: DatabaseOperations):
        self.db_ops = db_operations

    async def get_top_medical_equipment(self, limit: int = 20, state_code: Optional[str] = None) -> List[Dict]:
        """
        Get top medical equipment by frequency
        Returns items with CATMAT codes and match frequency
        """
        conn = None
        try:
            conn = await self.db_ops.db_manager.get_connection()

            params = [limit]
            query = """
                SELECT
                    unnest(ti.catmat_codes) as catmat_code,
                    COUNT(*) as frequency,
                    AVG(ti.homologated_unit_value) as avg_unit_price,
                    SUM(ti.quantity) as total_quantity,
                    COUNT(DISTINCT t.organization_id) as org_count
                FROM tender_items ti
                JOIN tenders t ON ti.tender_id = t.id
                WHERE ti.has_medical_catmat = TRUE
            """

            if state_code:
                query += " AND t.state_code = $2"
                params.append(state_code)

            query += """
                GROUP BY catmat_code
                ORDER BY frequency DESC
                LIMIT $1
            """

            results = await conn.fetch(query, *params)
            return [dict(row) for row in results]
        except Exception as e:
            logger.error(f"Error getting top medical equipment: {e}")
            return []
        finally:
            if conn:
                await conn.close()

    async def get_state_procurement_trends(self) -> List[Dict]:
        """Get procurement trends by state"""
        conn = None
        try:
            conn = await self.db_ops.db_manager.get_connection()

            query = """
                SELECT
                    t.state_code,
                    COUNT(DISTINCT t.id) as tender_count,
                    COUNT(DISTINCT t.organization_id) as org_count,
                    SUM(t.total_homologated_value) as total_value,
                    AVG(t.total_homologated_value) as avg_value,
                    COUNT(DISTINCT ti.catmat_codes) as unique_catmat_codes
                FROM tenders t
                LEFT JOIN tender_items ti ON t.id = ti.tender_id
                WHERE ti.has_medical_catmat = TRUE
                GROUP BY t.state_code
                ORDER BY total_value DESC
            """

            results = await conn.fetch(query)
            return [dict(row) for row in results]
        except Exception as e:
            logger.error(f"Error getting state trends: {e}")
            return []
        finally:
            if conn:
                await conn.close()

    async def get_top_medical_buyers(self, limit: int = 50, state_code: Optional[str] = None) -> List[Dict]:
        """Get top medical equipment buyers"""
        conn = None
        try:
            conn = await self.db_ops.db_manager.get_connection()

            params = [limit]
            query = """
                SELECT
                    o.name,
                    o.cnpj,
                    o.state_code,
                    o.organization_type,
                    COUNT(DISTINCT t.id) as tender_count,
                    SUM(t.total_homologated_value) as total_spending,
                    AVG(t.total_homologated_value) as avg_tender_value,
                    COUNT(DISTINCT ti.catmat_codes) as unique_products
                FROM organizations o
                JOIN tenders t ON o.id = t.organization_id
                LEFT JOIN tender_items ti ON t.id = ti.tender_id
                WHERE ti.has_medical_catmat = TRUE
            """

            if state_code:
                query += " AND o.state_code = $2"
                params.append(state_code)

            query += """
                GROUP BY o.id, o.name, o.cnpj, o.state_code, o.organization_type
                ORDER BY total_spending DESC
                LIMIT $1
            """

            results = await conn.fetch(query, *params)
            return [dict(row) for row in results]
        except Exception as e:
            logger.error(f"Error getting top buyers: {e}")
            return []
        finally:
            if conn:
                await conn.close()

    async def get_fernandes_opportunities(self, min_match_score: float = 60.0) -> List[Dict]:
        """Get procurement opportunities matching Fernandes products"""
        conn = None
        try:
            conn = await self.db_ops.db_manager.get_connection()

            query = """
                SELECT
                    mp.fernandes_product_code,
                    mp.fernandes_product_description,
                    COUNT(*) as match_count,
                    AVG(mp.match_score) as avg_match_score,
                    AVG(mp.price_comparison_brl) as avg_market_price,
                    AVG(mp.price_comparison_usd) as avg_fob_price,
                    AVG(mp.price_difference_percent) as avg_markup,
                    COUNT(CASE WHEN mp.is_competitive THEN 1 END) as competitive_count
                FROM matched_products mp
                WHERE mp.match_score >= $1
                GROUP BY mp.fernandes_product_code, mp.fernandes_product_description
                ORDER BY match_count DESC
            """

            results = await conn.fetch(query, min_match_score)
            return [dict(row) for row in results]
        except Exception as e:
            logger.error(f"Error getting Fernandes opportunities: {e}")
            return []
        finally:
            if conn:
                await conn.close()

    async def get_monthly_trends(self, months_back: int = 12, state_code: Optional[str] = None) -> List[Dict]:
        """Get monthly procurement trends"""
        conn = None
        try:
            conn = await self.db_ops.db_manager.get_connection()

            params = [months_back]
            query = """
                SELECT
                    DATE_TRUNC('month', t.publication_date) as month,
                    COUNT(DISTINCT t.id) as tender_count,
                    SUM(t.total_homologated_value) as total_value,
                    AVG(t.total_homologated_value) as avg_value,
                    COUNT(DISTINCT t.organization_id) as org_count
                FROM tenders t
                JOIN tender_items ti ON t.id = ti.tender_id
                WHERE ti.has_medical_catmat = TRUE
                  AND t.publication_date >= NOW() - ($1::text || ' months')::INTERVAL
            """

            if state_code:
                query += " AND t.state_code = $2"
                params.append(state_code)

            query += """
                GROUP BY month
                ORDER BY month DESC
            """

            results = await conn.fetch(query, *params)
            return [dict(row) for row in results]
        except Exception as e:
            logger.error(f"Error getting monthly trends: {e}")
            return []
        finally:
            if conn:
                await conn.close()

    async def generate_comprehensive_report(self, state_code: Optional[str] = None) -> Dict[str, Any]:
        """Generate comprehensive analytics report"""

        logger.info(f"Generating comprehensive analytics report{' for ' + state_code if state_code else ''}")

        report = {
            'generated_at': datetime.now().isoformat(),
            'state_filter': state_code,
            'top_equipment': await self.get_top_medical_equipment(limit=20, state_code=state_code),
            'state_trends': await self.get_state_procurement_trends() if not state_code else [],
            'top_buyers': await self.get_top_medical_buyers(limit=30, state_code=state_code),
            'fernandes_opportunities': await self.get_fernandes_opportunities(),
            'monthly_trends': await self.get_monthly_trends(months_back=6, state_code=state_code)
        }

        return report

    def export_report_to_json(self, report: Dict[str, Any], output_file: str):
        """Export report to JSON file"""
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False, default=str)
            logger.info(f"Report exported to {output_file}")
        except Exception as e:
            logger.error(f"Error exporting report: {e}")


def print_performance_summary(tracker: PerformanceTracker):
    """Print formatted performance summary"""
    summary = tracker.get_summary()

    if not summary:
        print("No performance data available")
        return

    print("\n" + "="*70)
    print("📊 PERFORMANCE SUMMARY")
    print("="*70)
    print(f"Total Operations: {summary['total_operations']}")
    print(f"Total Tenders Processed: {summary['total_tenders_processed']:,}")
    print(f"Total API Calls: {summary['total_api_calls']:,}")
    print(f"Total Duration: {summary['total_duration_seconds']:.2f}s")
    print(f"Average Throughput: {summary['average_throughput']:.2f} tenders/second")
    print(f"API Efficiency: {summary['api_efficiency']:.2f} tenders/API call")
    print(f"Total Errors: {summary['total_errors']}")

    print("\n--- Operation Breakdown ---")
    for op in summary['operations']:
        print(f"\n{op['name']}:")
        print(f"  Duration: {op['duration']:.2f}s")
        print(f"  Tenders: {op['tenders']:,}")
        print(f"  API Calls: {op['api_calls']:,}")
        print(f"  Throughput: {op['throughput']:.2f} tenders/s")
        if op['errors'] > 0:
            print(f"  Errors: {op['errors']}")

    print("="*70 + "\n")


def print_analytics_report(report: Dict[str, Any]):
    """Print formatted analytics report"""
    print("\n" + "="*70)
    print("📈 MEDICAL PROCUREMENT ANALYTICS REPORT")
    print("="*70)
    print(f"Generated: {report['generated_at']}")
    if report['state_filter']:
        print(f"State Filter: {report['state_filter']}")

    # Top Equipment
    if report['top_equipment']:
        print("\n--- Top 10 Medical Equipment (by frequency) ---")
        for i, item in enumerate(report['top_equipment'][:10], 1):
            print(f"{i}. CATMAT {item['catmat_code']}: {item['frequency']} occurrences")
            print(f"   Avg Price: R${item.get('avg_unit_price', 0):,.2f}")
            print(f"   Used by: {item['org_count']} organizations")

    # Top Buyers
    if report['top_buyers']:
        print("\n--- Top 10 Medical Buyers (by spending) ---")
        for i, buyer in enumerate(report['top_buyers'][:10], 1):
            print(f"{i}. {buyer['name']}")
            print(f"   Total Spending: R${buyer['total_spending']:,.2f}")
            print(f"   Tenders: {buyer['tender_count']}")
            print(f"   State: {buyer['state_code']}")

    # Fernandes Opportunities
    if report['fernandes_opportunities']:
        print("\n--- Top 10 Fernandes Product Opportunities ---")
        for i, opp in enumerate(report['fernandes_opportunities'][:10], 1):
            print(f"{i}. {opp['fernandes_product_code']}: {opp['fernandes_product_description'][:50]}")
            print(f"   Matches: {opp['match_count']}")
            print(f"   Avg Match Score: {opp['avg_match_score']:.1f}%")
            print(f"   Avg Market Price: R${opp['avg_market_price']:,.2f}")
            print(f"   Competitive: {opp['competitive_count']}/{opp['match_count']}")

    print("="*70 + "\n")


# Example usage
async def example_analytics():
    """Example analytics workflow"""
    from database import CloudSQLManager

    # Initialize
    db_manager = CloudSQLManager()
    db_ops = DatabaseOperations(db_manager)
    analytics = MedicalProcurementAnalytics(db_ops)

    # Generate report for São Paulo
    report = await analytics.generate_comprehensive_report(state_code='SP')

    # Print report
    print_analytics_report(report)

    # Export to JSON
    analytics.export_report_to_json(report, 'medical_analytics_SP.json')


if __name__ == "__main__":
    import asyncio
    asyncio.run(example_analytics())
