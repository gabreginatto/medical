#!/usr/bin/env python3
"""
Simple test to verify PNCP API accessibility
Tests the public Consultation API endpoints without authentication
"""

import asyncio
import aiohttp
from datetime import datetime, timedelta

# PNCP API Configuration
CONSULTATION_BASE_URL = "https://pncp.gov.br/api/consulta"

async def test_api_basic_access():
    """Test basic API accessibility"""
    print("=" * 70)
    print("PNCP API Accessibility Test")
    print("=" * 70)
    print("\n1. Testing basic API endpoint accessibility...")

    try:
        async with aiohttp.ClientSession() as session:
            # Test the base consultation API
            url = f"{CONSULTATION_BASE_URL}/v1/contratacoes/publicacao"

            # Use a recent date range for testing
            end_date = datetime.now()
            start_date = end_date - timedelta(days=7)

            params = {
                'dataInicial': start_date.strftime('%Y%m%d'),
                'dataFinal': end_date.strftime('%Y%m%d'),
                'codigoModalidadeContratacao': 8,  # Dispensa de Licitação
                'uf': 'DF',  # Federal District
                'pagina': 1,
                'tamanhoPagina': 10  # Small page size for testing
            }

            print(f"   URL: {url}")
            print(f"   Date range: {params['dataInicial']} to {params['dataFinal']}")
            print(f"   State: DF (Federal District)")
            print(f"   Modality: 8 (Dispensa de Licitação)")

            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=30)) as response:
                status_code = response.status

                print(f"\n   Response Status: {status_code}")

                if status_code == 200:
                    data = await response.json()

                    total_records = data.get('totalRegistros', 0)
                    total_pages = data.get('totalPaginas', 0)
                    page_number = data.get('numeroPagina', 0)
                    records = data.get('data', [])

                    print(f"   ✅ API is accessible!")
                    print(f"\n   Response Data:")
                    print(f"   - Total Records Found: {total_records}")
                    print(f"   - Total Pages: {total_pages}")
                    print(f"   - Current Page: {page_number}")
                    print(f"   - Records in this page: {len(records)}")

                    if records:
                        print(f"\n   Sample Tender (first result):")
                        first_tender = records[0]
                        print(f"   - Control Number: {first_tender.get('numeroControlePNCP', 'N/A')}")
                        print(f"   - Organization: {first_tender.get('orgaoEntidade', {}).get('razaoSocial', 'N/A')}")
                        print(f"   - Modality: {first_tender.get('modalidadeNome', 'N/A')}")
                        est_value = first_tender.get('valorTotalEstimado', 0) or 0
                        hom_value = first_tender.get('valorTotalHomologado', 0) or 0
                        print(f"   - Estimated Value: R$ {est_value:,.2f}")
                        print(f"   - Homologated Value: R$ {hom_value:,.2f}")

                    return True

                elif status_code == 204:
                    print(f"   ✅ API is accessible!")
                    print(f"   ℹ️  No tenders found for the specified criteria (this is normal)")
                    return True

                elif status_code == 401:
                    print(f"   ❌ Authentication error (unexpected - API should be public)")
                    print(f"   Response: {await response.text()}")
                    return False

                elif status_code == 429:
                    print(f"   ⚠️  Rate limit reached - API is accessible but too many requests")
                    return True

                else:
                    print(f"   ❌ Unexpected status code: {status_code}")
                    print(f"   Response: {await response.text()}")
                    return False

    except aiohttp.ClientError as e:
        print(f"   ❌ Network error: {e}")
        return False
    except asyncio.TimeoutError:
        print(f"   ❌ Request timeout - API might be slow or unreachable")
        return False
    except Exception as e:
        print(f"   ❌ Unexpected error: {e}")
        return False

async def test_api_swagger_docs():
    """Test if Swagger documentation is accessible"""
    print("\n2. Testing API documentation accessibility...")

    swagger_url = "https://pncp.gov.br/api/consulta/swagger-ui/index.html"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(swagger_url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    print(f"   ✅ API Documentation accessible at: {swagger_url}")
                    return True
                else:
                    print(f"   ⚠️  Documentation returned status {response.status}")
                    return False
    except Exception as e:
        print(f"   ⚠️  Could not access documentation: {e}")
        return False

async def test_multiple_states():
    """Test API access for multiple states"""
    print("\n3. Testing API access across multiple states...")

    test_states = ['DF', 'SP', 'RJ', 'MG', 'BA']
    results = {}

    async with aiohttp.ClientSession() as session:
        for state in test_states:
            try:
                url = f"{CONSULTATION_BASE_URL}/v1/contratacoes/publicacao"

                # Use a small recent date range
                end_date = datetime.now()
                start_date = end_date - timedelta(days=3)

                params = {
                    'dataInicial': start_date.strftime('%Y%m%d'),
                    'dataFinal': end_date.strftime('%Y%m%d'),
                    'codigoModalidadeContratacao': 6,  # Pregão Eletrônico
                    'uf': state,
                    'pagina': 1,
                    'tamanhoPagina': 10  # Minimum allowed by API
                }

                async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status in [200, 204]:
                        data = await response.json() if response.status == 200 else {}
                        total = data.get('totalRegistros', 0)
                        results[state] = total
                        print(f"   ✅ {state}: {total} tenders found")
                    else:
                        results[state] = -1
                        error_text = await response.text()
                        print(f"   ❌ {state}: Error {response.status} - {error_text[:100]}")

                # Small delay between requests
                await asyncio.sleep(0.2)

            except Exception as e:
                results[state] = -1
                print(f"   ❌ {state}: {e}")

    success_count = sum(1 for v in results.values() if v >= 0)
    print(f"\n   Summary: {success_count}/{len(test_states)} states accessible")

    return success_count == len(test_states)

async def main():
    """Run all tests"""
    print("\n🔍 Starting PNCP API Accessibility Tests\n")

    results = []

    # Test 1: Basic API access
    result1 = await test_api_basic_access()
    results.append(result1)

    # Test 2: Documentation
    result2 = await test_api_swagger_docs()
    results.append(result2)

    # Test 3: Multiple states
    result3 = await test_multiple_states()
    results.append(result3)

    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    test_names = [
        "Basic API Access",
        "API Documentation",
        "Multiple States Access"
    ]

    for i, (name, result) in enumerate(zip(test_names, results), 1):
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{i}. {name}: {status}")

    passed = sum(results)
    total = len(results)

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All tests passed! PNCP API is fully accessible.")
        print("\n📝 Next steps:")
        print("   1. The PNCP API is working correctly")
        print("   2. No authentication required (as expected)")
        print("   3. You can now run the full data processing pipeline")
    elif passed > 0:
        print("\n⚠️  Some tests passed - API is accessible but there may be issues")
    else:
        print("\n❌ All tests failed - Check your internet connection")
        print("   - Verify you can access https://pncp.gov.br")
        print("   - Check for firewall or proxy restrictions")

    print("\n" + "=" * 70)

if __name__ == "__main__":
    asyncio.run(main())