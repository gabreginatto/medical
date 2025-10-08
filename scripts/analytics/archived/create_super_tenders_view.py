"""Create super_tenders materialized view"""
import asyncio
from google.cloud.sql.connector import Connector

async def create_view():
    connector = Connector()

    try:
        conn = await connector.connect_async(
            "medical-473219:us-central1:pncp-medical-db",
            "asyncpg",
            user="postgres",
            password="TempPass123!",
            db="pncp_medical_data"
        )

        print("Creating analytics.super_tenders view...\n")

        sql = """
CREATE MATERIALIZED VIEW analytics.super_tenders AS
WITH tender_item_counts AS (
    SELECT
        tender_id,
        COUNT(*) as item_count,
        SUM(homologated_total_value) as items_total_value
    FROM tender_items
    WHERE homologated_total_value > 0
    GROUP BY tender_id
)
SELECT
    t.id as tender_id,
    t.control_number,
    t.year as tender_year,
    t.publication_date,
    t.total_homologated_value,

    -- Item statistics
    tic.item_count,
    tic.items_total_value,
    ROUND((t.total_homologated_value / tic.item_count)::numeric, 2) as avg_value_per_item,

    -- Organization details
    o.name as organization_name,
    o.cnpj as organization_cnpj,
    o.state_code,
    o.government_level,
    o.organization_type,

    -- Tender details
    t.modality_code,

    -- Value category
    CASE
        WHEN t.total_homologated_value >= 1000000 THEN 'Mega (>R$1M)'
        WHEN t.total_homologated_value >= 500000 THEN 'Large (R$500K-1M)'
        WHEN t.total_homologated_value >= 100000 THEN 'Medium (R$100K-500K)'
        ELSE 'Small (<R$100K)'
    END as value_category,

    -- Efficiency score (higher value / fewer items = higher score)
    ROUND((t.total_homologated_value / tic.item_count)::numeric, 0) as efficiency_score

FROM tenders t
JOIN tender_item_counts tic ON t.id = tic.tender_id
JOIN organizations o ON t.organization_id = o.id
WHERE tic.item_count BETWEEN 2 AND 5  -- Only 2-5 items
  AND t.total_homologated_value >= 50000  -- At least R$50k
ORDER BY t.total_homologated_value DESC;

CREATE INDEX idx_analytics_super_tenders_value ON analytics.super_tenders(total_homologated_value DESC);
CREATE INDEX idx_analytics_super_tenders_item_count ON analytics.super_tenders(item_count);
CREATE INDEX idx_analytics_super_tenders_state ON analytics.super_tenders(state_code);
CREATE INDEX idx_analytics_super_tenders_efficiency ON analytics.super_tenders(efficiency_score DESC);
"""

        await conn.execute(sql)
        print("✅ View created successfully!")

        # Count rows
        count = await conn.fetchval("SELECT COUNT(*) FROM analytics.super_tenders")
        print(f"📊 Found {count} super tenders!\n")

        # Show top 5 examples
        results = await conn.fetch("""
            SELECT
                control_number,
                organization_name,
                state_code,
                item_count,
                total_homologated_value,
                avg_value_per_item,
                value_category
            FROM analytics.super_tenders
            ORDER BY total_homologated_value DESC
            LIMIT 5
        """)

        print("Top 5 Super Tenders:")
        print("="*100)
        for i, row in enumerate(results, 1):
            print(f"{i}. {row['organization_name'][:50]} ({row['state_code']})")
            print(f"   Control: {row['control_number']}")
            print(f"   Items: {row['item_count']} | Total: R${row['total_homologated_value']:,.2f} | Avg/Item: R${row['avg_value_per_item']:,.2f}")
            print(f"   Category: {row['value_category']}")
            print()

        await conn.close()
    finally:
        await connector.close_async()

asyncio.run(create_view())
