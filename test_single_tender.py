#!/usr/bin/env python3
"""
Test saving a single tender to database to verify schema
"""

import asyncio
import logging
from database import create_db_manager_from_env, DatabaseOperations
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_single_tender():
    """Test saving one medical tender from the discovered set"""

    # Use a tender we know exists from the test: 12474705000120-1-000107/2024
    # Control number format: cnpj-modalidade-sequencial/ano

    test_tender = {
        'numeroControlePNCP': '12474705000120-1-000107/2024',
        'objetoCompra': 'AQUISIÇÃO DE EQUIPAMENTOS MÉDICOS HOSPITALARES',
        'valorTotalEstimado': 150000.00,
        'valorTotalHomologado': 145000.00,
        'dataPublicacaoPncp': '2024-07-15',
        'modalidadeId': 1,
        'modalidadeNome': 'Concorrência Eletrônica',
        'anoCompra': 2024,
        'sequencial': 107,
        'uf': 'SP',
        'government_level': 'municipal',
        'tender_size': 'medium',
        'medical_confidence': 85.0,
        'orgaoEntidade': {
            'cnpj': '12474705000120',
            'razaoSocial': 'PREFEITURA MUNICIPAL DE SANTO ANDRÉ'
        }
    }

    print("=" * 70)
    print("🧪 SINGLE TENDER DATABASE TEST")
    print("=" * 70)
    print(f"\nTesting tender: {test_tender['numeroControlePNCP']}")
    print(f"Organization: {test_tender['orgaoEntidade']['razaoSocial']}")
    print(f"Value: R$ {test_tender['valorTotalEstimado']:,.2f}")

    db_manager = None

    try:
        # Initialize database
        print("\n1️⃣  Connecting to database...")
        db_manager = create_db_manager_from_env()
        db_ops = DatabaseOperations(db_manager)
        print("   ✅ Connected")

        # Insert organization
        print("\n2️⃣  Inserting organization...")
        org_data = test_tender['orgaoEntidade']

        org_id = await db_ops.insert_organization({
            'cnpj': org_data['cnpj'],
            'name': org_data['razaoSocial'],
            'government_level': test_tender.get('government_level', 'unknown'),
            'state_code': test_tender.get('uf', 'SP')
        })

        print(f"   ✅ Organization saved with ID: {org_id}")

        # Insert tender
        print("\n3️⃣  Inserting tender...")
        control_num = test_tender['numeroControlePNCP']

        tender_id = await db_ops.insert_tender({
            'organization_id': org_id,
            'control_number': control_num
        })

        print(f"   ✅ Tender saved with ID: {tender_id}")

        print("\n" + "=" * 70)
        print("✅ SUCCESS - Tender saved to database!")
        print("=" * 70)
        print(f"Organization ID: {org_id}")
        print(f"Tender ID: {tender_id}")
        print(f"Control Number: {control_num}")

    except Exception as e:
        print("\n" + "=" * 70)
        print("❌ ERROR")
        print("=" * 70)
        print(f"Error: {e}")
        logger.error(f"Test failed: {e}", exc_info=True)
        raise

    finally:
        if db_manager:
            await db_manager.close()
            print("\n🔒 Database connection closed")

if __name__ == "__main__":
    asyncio.run(test_single_tender())
