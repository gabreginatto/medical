#!/usr/bin/env python3
"""Export all items with 'curativo' in description to markdown file"""

from dotenv import load_dotenv
load_dotenv()

import asyncio
from database import create_db_manager_from_env

async def get_curativo_items():
    db = create_db_manager_from_env()

    query = """
    SELECT
        ti.id,
        ti.description,
        ti.unit,
        ti.quantity,
        ti.estimated_unit_value,
        ti.homologated_unit_value,
        ti.winner_name,
        t.control_number,
        t.state_code,
        o.name as organization_name
    FROM tender_items ti
    JOIN tenders t ON ti.tender_id = t.id
    JOIN organizations o ON t.organization_id = o.id
    WHERE LOWER(ti.description) LIKE '%curativo%'
    ORDER BY ti.homologated_unit_value DESC NULLS LAST;
    """

    conn = await db.get_connection()
    rows = await conn.fetch(query)
    await conn.close()
    await db.close()

    return rows

async def main():
    items = await get_curativo_items()

    # Create markdown file
    md_content = f"""# Curativo Items Found in Database

**Total items found:** {len(items)}

---

"""

    for i, item in enumerate(items, 1):
        est_price = f"R$ {item['estimated_unit_value']:.4f}" if item['estimated_unit_value'] else 'N/A'
        hom_price = f"R$ {item['homologated_unit_value']:.4f}" if item['homologated_unit_value'] else 'N/A'

        md_content += f"""## {i}. {item['description']}

- **Organization:** {item['organization_name']}
- **State:** {item['state_code']}
- **Tender:** {item['control_number']}
- **Unit:** {item['unit']}
- **Quantity:** {item['quantity']}
- **Estimated Price:** {est_price}
- **Homologated Price:** {hom_price}
- **Winner:** {item['winner_name'] or 'N/A'}

---

"""

    # Write to file
    with open('curativo_items.md', 'w') as f:
        f.write(md_content)

    print(f"✅ Found {len(items)} items with 'curativo' in the description")
    print(f"📝 Saved to curativo_items.md")

if __name__ == "__main__":
    asyncio.run(main())
