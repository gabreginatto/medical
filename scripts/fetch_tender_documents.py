#!/usr/bin/env python3
"""
PNCP Tender Documents Fetcher
Fetches Editais, Historico, and Ata documents from PNCP API
"""

import asyncio
import argparse
import os
import json
from datetime import datetime
from pathlib import Path
import sys

# Add parent directory to path to import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pncp_api import PNCPAPIClient


class TenderDocumentFetcher:
    """Fetches documents and data for PNCP tenders"""

    def __init__(self, output_dir: str = "tender_documents"):
        """
        Initialize the document fetcher

        Args:
            output_dir: Directory to save downloaded documents
        """
        self.client = PNCPAPIClient()
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

    def _get_tender_dir(self, cnpj: str, year: int, sequential: int) -> Path:
        """
        Get tender directory path using control number format

        Format: CNPJ-1-SEQUENTIAL-YEAR (with / replaced by - for filesystem)
        Example: 13864377000130-1-000537-2025
        """
        control_number = f"{cnpj}-1-{sequential:06d}-{year}"
        return self.output_dir / control_number

    async def fetch_tender_documents(self, cnpj: str, year: int, sequential: int,
                                    download: bool = False) -> dict:
        """
        Fetch all documents for a tender

        Args:
            cnpj: Organization CNPJ (with or without formatting)
            year: Tender year
            sequential: Tender sequential number
            download: If True, download document files

        Returns:
            Dictionary with document metadata
        """
        # Ensure session is started
        await self.client.start_session()

        # Clean CNPJ
        cnpj = cnpj.replace('.', '').replace('/', '').replace('-', '')

        url = f"{self.client.pncp_url}/v1/orgaos/{cnpj}/compras/{year}/{sequential}/arquivos"

        print(f"\n{'='*80}")
        print(f"Fetching documents for tender: {cnpj}-1-{sequential:06d}/{year}")
        print(f"URL: {url}")
        print(f"{'='*80}\n")

        try:
            async with self.client.session.get(url) as response:
                if response.status == 200:
                    documents = await response.json()

                    print(f"✅ Found {len(documents)} documents\n")

                    for idx, doc in enumerate(documents, 1):
                        print(f"Document #{idx}:")
                        print(f"  Title: {doc.get('titulo', 'N/A')}")
                        print(f"  Type: {doc.get('tipoDocumentoNome', 'N/A')}")
                        print(f"  Description: {doc.get('tipoDocumentoDescricao', 'N/A')}")
                        print(f"  Sequential: {doc.get('sequencialDocumento', 'N/A')}")
                        print(f"  URI: {doc.get('uri', 'N/A')}")
                        print(f"  URL: {doc.get('url', 'N/A')}")
                        print(f"  Published: {doc.get('dataPublicacaoPncp', 'N/A')}")
                        print(f"  Active: {doc.get('statusAtivo', 'N/A')}")
                        print()

                        # Download document if requested
                        if download and doc.get('sequencialDocumento'):
                            await self.download_document(
                                cnpj, year, sequential,
                                doc['sequencialDocumento'],
                                doc.get('titulo', f"document_{doc['sequencialDocumento']}")
                            )

                    return {
                        'success': True,
                        'count': len(documents),
                        'documents': documents
                    }
                elif response.status == 404:
                    print(f"❌ Tender not found or has no documents")
                    return {'success': False, 'error': 'Not found', 'documents': []}
                else:
                    error_text = await response.text()
                    print(f"❌ Error {response.status}: {error_text}")
                    return {'success': False, 'error': error_text, 'documents': []}

        except Exception as e:
            print(f"❌ Exception: {e}")
            return {'success': False, 'error': str(e), 'documents': []}

    async def download_document(self, cnpj: str, year: int, sequential: int,
                               doc_sequential: int, doc_title: str) -> bool:
        """
        Download a specific document

        Args:
            cnpj: Organization CNPJ
            year: Tender year
            sequential: Tender sequential number
            doc_sequential: Document sequential number
            doc_title: Document title for filename

        Returns:
            True if successful, False otherwise
        """
        cnpj = cnpj.replace('.', '').replace('/', '').replace('-', '')

        url = f"{self.client.pncp_url}/v1/orgaos/{cnpj}/compras/{year}/{sequential}/arquivos/{doc_sequential}"

        print(f"  📥 Downloading: {doc_title}...")

        try:
            async with self.client.session.get(url) as response:
                if response.status == 200:
                    # Create tender-specific directory
                    tender_dir = self._get_tender_dir(cnpj, year, sequential)
                    tender_dir.mkdir(exist_ok=True)

                    # Sanitize filename
                    safe_title = "".join(c for c in doc_title if c.isalnum() or c in (' ', '-', '_')).strip()
                    filename = tender_dir / f"{doc_sequential}_{safe_title}.pdf"

                    # Save file
                    content = await response.read()
                    with open(filename, 'wb') as f:
                        f.write(content)

                    print(f"  ✅ Saved to: {filename} ({len(content):,} bytes)")
                    return True
                else:
                    print(f"  ❌ Download failed: {response.status}")
                    return False

        except Exception as e:
            print(f"  ❌ Download exception: {e}")
            return False

    async def fetch_tender_history(self, cnpj: str, year: int, sequential: int) -> dict:
        """
        Fetch historic price data for a tender

        Args:
            cnpj: Organization CNPJ
            year: Tender year
            sequential: Tender sequential number

        Returns:
            Dictionary with history data
        """
        # Ensure session is started
        await self.client.start_session()

        cnpj = cnpj.replace('.', '').replace('/', '').replace('-', '')

        url = f"{self.client.pncp_url}/v1/orgaos/{cnpj}/compras/{year}/{sequential}/historico"

        print(f"\n{'='*80}")
        print(f"Fetching history for tender: {cnpj}-1-{sequential:06d}/{year}")
        print(f"URL: {url}")
        print(f"{'='*80}\n")

        try:
            async with self.client.session.get(url) as response:
                if response.status == 200:
                    history = await response.json()

                    print(f"✅ Found {len(history)} history records\n")

                    for idx, record in enumerate(history, 1):
                        print(f"History Record #{idx}:")
                        print(f"  Type: {record.get('tipoLogManutencaoNome', 'N/A')}")
                        print(f"  Category: {record.get('categoriaLogManutencaoNome', 'N/A')}")
                        print(f"  Date: {record.get('logManutencaoDataInclusao', 'N/A')}")
                        print(f"  Document Title: {record.get('documentoTitulo', 'N/A')}")
                        print(f"  Document Type: {record.get('documentoTipo', 'N/A')}")
                        print(f"  Item Number: {record.get('itemNumero', 'N/A')}")
                        print(f"  Justification: {record.get('justificativa', 'N/A')}")
                        print()

                    return {
                        'success': True,
                        'count': len(history),
                        'history': history
                    }
                elif response.status == 404:
                    print(f"❌ No history found")
                    return {'success': False, 'error': 'Not found', 'history': []}
                else:
                    error_text = await response.text()
                    print(f"❌ Error {response.status}: {error_text}")
                    return {'success': False, 'error': error_text, 'history': []}

        except Exception as e:
            print(f"❌ Exception: {e}")
            return {'success': False, 'error': str(e), 'history': []}

    async def fetch_tender_atas(self, cnpj: str, year: int, sequential: int,
                               download: bool = False) -> dict:
        """
        Fetch price registration records (Atas) for a tender

        Args:
            cnpj: Organization CNPJ
            year: Tender year
            sequential: Tender sequential number
            download: If True, download ata documents

        Returns:
            Dictionary with ata data
        """
        # Ensure session is started
        await self.client.start_session()

        cnpj = cnpj.replace('.', '').replace('/', '').replace('-', '')

        url = f"{self.client.pncp_url}/v1/orgaos/{cnpj}/compras/{year}/{sequential}/atas"

        print(f"\n{'='*80}")
        print(f"Fetching Atas for tender: {cnpj}-1-{sequential:06d}/{year}")
        print(f"URL: {url}")
        print(f"{'='*80}\n")

        try:
            async with self.client.session.get(url) as response:
                if response.status == 200:
                    response_data = await response.json()

                    # Handle paginated response
                    if isinstance(response_data, dict) and 'data' in response_data:
                        atas = response_data['data']
                    elif isinstance(response_data, list):
                        atas = response_data
                    else:
                        print(f"⚠️  Unexpected response format: {type(response_data)}")
                        print(f"Response keys: {response_data.keys() if isinstance(response_data, dict) else 'Not a dict'}")
                        return {'success': False, 'error': 'Unexpected response format', 'atas': []}

                    print(f"✅ Found {len(atas)} Atas\n")

                    # Handle different response formats
                    processed_atas = []
                    for idx, ata in enumerate(atas, 1):
                        try:
                            # Check if ata is a dict (expected format)
                            if isinstance(ata, dict):
                                print(f"Ata #{idx}:")
                                print(f"  Number: {ata.get('numeroAtaRegistroPreco', 'N/A')}")
                                print(f"  Sequential: {ata.get('sequencialAta', 'N/A')}")
                                print(f"  Control Number: {ata.get('numeroControlePNCP', 'N/A')}")
                                print(f"  Signature Date: {ata.get('dataAssinatura', 'N/A')}")
                                print(f"  Validity: {ata.get('dataVigenciaInicio', 'N/A')} to {ata.get('dataVigenciaFim', 'N/A')}")
                                print(f"  Canceled: {ata.get('cancelado', False)}")
                                print()

                                processed_atas.append(ata)

                                # Fetch ata documents if requested
                                if download and ata.get('sequencialAta'):
                                    await self.fetch_ata_documents(
                                        cnpj, year, sequential,
                                        ata['sequencialAta'],
                                        download=True
                                    )
                            elif isinstance(ata, str):
                                # If it's a string, it might be a control number or URL
                                print(f"Ata #{idx}: {ata}")
                                processed_atas.append({'raw': ata})
                            else:
                                print(f"Ata #{idx}: Unexpected format - {type(ata)}")
                                print(f"  Data: {ata}")
                                processed_atas.append({'raw': str(ata)})

                        except Exception as e:
                            print(f"❌ Error processing Ata #{idx}: {e}")
                            print(f"   Ata data type: {type(ata)}")
                            print(f"   Ata data: {ata}")
                            continue

                    return {
                        'success': True,
                        'count': len(processed_atas),
                        'atas': processed_atas
                    }
                elif response.status == 404:
                    print(f"❌ No Atas found")
                    return {'success': False, 'error': 'Not found', 'atas': []}
                else:
                    error_text = await response.text()
                    print(f"❌ Error {response.status}: {error_text}")
                    return {'success': False, 'error': error_text, 'atas': []}

        except Exception as e:
            print(f"❌ Exception: {e}")
            return {'success': False, 'error': str(e), 'atas': []}

    async def fetch_ata_documents(self, cnpj: str, year: int, sequential: int,
                                 ata_sequential: int, download: bool = False) -> dict:
        """
        Fetch documents for a specific Ata

        Args:
            cnpj: Organization CNPJ
            year: Tender year
            sequential: Tender sequential number
            ata_sequential: Ata sequential number
            download: If True, download document files

        Returns:
            Dictionary with ata document metadata
        """
        cnpj = cnpj.replace('.', '').replace('/', '').replace('-', '')

        url = f"{self.client.pncp_url}/v1/orgaos/{cnpj}/compras/{year}/{sequential}/atas/{ata_sequential}/arquivos"

        print(f"  Fetching documents for Ata #{ata_sequential}...")

        try:
            async with self.client.session.get(url) as response:
                if response.status == 200:
                    documents = await response.json()

                    print(f"  ✅ Found {len(documents)} documents in Ata")

                    for doc in documents:
                        print(f"    - {doc.get('titulo', 'N/A')} (Type: {doc.get('tipoDocumentoNome', 'N/A')})")

                        if download and doc.get('sequencialDocumento'):
                            await self.download_ata_document(
                                cnpj, year, sequential, ata_sequential,
                                doc['sequencialDocumento'],
                                doc.get('titulo', f"ata_document_{doc['sequencialDocumento']}")
                            )

                    return {
                        'success': True,
                        'count': len(documents),
                        'documents': documents
                    }
                else:
                    print(f"  ❌ No documents found for Ata")
                    return {'success': False, 'documents': []}

        except Exception as e:
            print(f"  ❌ Exception: {e}")
            return {'success': False, 'error': str(e), 'documents': []}

    async def download_ata_document(self, cnpj: str, year: int, sequential: int,
                                   ata_sequential: int, doc_sequential: int,
                                   doc_title: str) -> bool:
        """
        Download a specific ata document

        Args:
            cnpj: Organization CNPJ
            year: Tender year
            sequential: Tender sequential number
            ata_sequential: Ata sequential number
            doc_sequential: Document sequential number
            doc_title: Document title for filename

        Returns:
            True if successful, False otherwise
        """
        cnpj = cnpj.replace('.', '').replace('/', '').replace('-', '')

        url = f"{self.client.pncp_url}/v1/orgaos/{cnpj}/compras/{year}/{sequential}/atas/{ata_sequential}/arquivos/{doc_sequential}"

        print(f"    📥 Downloading: {doc_title}...")

        try:
            async with self.client.session.get(url) as response:
                if response.status == 200:
                    # Create tender-specific directory
                    tender_dir = self._get_tender_dir(cnpj, year, sequential) / "atas"
                    tender_dir.mkdir(parents=True, exist_ok=True)

                    # Sanitize filename
                    safe_title = "".join(c for c in doc_title if c.isalnum() or c in (' ', '-', '_')).strip()
                    filename = tender_dir / f"ata_{ata_sequential}_{doc_sequential}_{safe_title}.pdf"

                    # Save file
                    content = await response.read()
                    with open(filename, 'wb') as f:
                        f.write(content)

                    print(f"    ✅ Saved to: {filename} ({len(content):,} bytes)")
                    return True
                else:
                    print(f"    ❌ Download failed: {response.status}")
                    return False

        except Exception as e:
            print(f"    ❌ Download exception: {e}")
            return False

    async def fetch_all(self, cnpj: str, year: int, sequential: int,
                       download: bool = False, save_json: bool = True):
        """
        Fetch all data for a tender: documents, history, and atas

        Args:
            cnpj: Organization CNPJ
            year: Tender year
            sequential: Tender sequential number
            download: If True, download all documents
            save_json: If True, save JSON metadata
        """
        print(f"\n{'#'*80}")
        print(f"# Fetching ALL data for tender: {cnpj}-1-{sequential:06d}/{year}")
        print(f"{'#'*80}\n")

        results = {}

        # Fetch documents
        results['documents'] = await self.fetch_tender_documents(cnpj, year, sequential, download)

        # Fetch history
        results['history'] = await self.fetch_tender_history(cnpj, year, sequential)

        # Fetch atas
        results['atas'] = await self.fetch_tender_atas(cnpj, year, sequential, download)

        # Save JSON if requested
        if save_json:
            cnpj_clean = cnpj.replace('.', '').replace('/', '').replace('-', '')
            tender_dir = self._get_tender_dir(cnpj_clean, year, sequential)
            tender_dir.mkdir(exist_ok=True)

            json_file = tender_dir / "metadata.json"
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2, default=str)

            print(f"\n💾 Metadata saved to: {json_file}")

        print(f"\n{'#'*80}")
        print(f"# Summary")
        print(f"{'#'*80}")
        print(f"Documents: {results['documents'].get('count', 0)}")
        print(f"History Records: {results['history'].get('count', 0)}")
        print(f"Atas: {results['atas'].get('count', 0)}")

        # Show folder location
        cnpj_clean = cnpj.replace('.', '').replace('/', '').replace('-', '')
        control_num = f"{cnpj_clean}-1-{sequential:06d}/{year}"
        folder_name = f"{cnpj_clean}-1-{sequential:06d}-{year}"
        print(f"\n📁 All files saved to: {self.output_dir / folder_name}")
        print(f"   (Control number: {control_num})")
        print(f"{'#'*80}\n")

        return results

    async def close(self):
        """Close the client session"""
        await self.client.close_session()


def parse_control_number(control_number: str) -> tuple:
    """
    Parse PNCP control number into components

    Format: {CNPJ}-1-{SEQUENTIAL}/{YEAR}
    Example: 46374500000194-1-006949/2025

    Returns:
        tuple: (cnpj, year, sequential)
    """
    try:
        # Split by '/' to get year
        parts = control_number.split('/')
        if len(parts) != 2:
            raise ValueError(f"Invalid control number format: {control_number}")

        year = int(parts[1])

        # Split first part by '-'
        left_parts = parts[0].split('-')
        if len(left_parts) != 3:
            raise ValueError(f"Invalid control number format: {control_number}")

        cnpj = left_parts[0]
        sequential = int(left_parts[2])

        return cnpj, year, sequential

    except Exception as e:
        raise ValueError(f"Error parsing control number '{control_number}': {e}")


async def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description='Fetch tender documents, history, and atas from PNCP',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Using control number (easiest!)
  python fetch_tender_documents.py --control-number "46374500000194-1-006949/2025"

  # Using control number with download
  python fetch_tender_documents.py --control-number "46374500000194-1-006949/2025" --download

  # Using individual components
  python fetch_tender_documents.py --cnpj 46374500000194 --year 2025 --sequential 6949

  # Fetch and download all documents
  python fetch_tender_documents.py --cnpj 46374500000194 --year 2025 --sequential 6949 --download

  # Fetch only documents (no history or atas)
  python fetch_tender_documents.py --control-number "46374500000194-1-006949/2025" --documents-only

  # Custom output directory
  python fetch_tender_documents.py --control-number "46374500000194-1-006949/2025" --output my_docs
        """
    )

    # Control number OR individual components
    parser.add_argument('--control-number', '--control', help='PNCP control number (format: CNPJ-1-SEQUENTIAL/YEAR)')
    parser.add_argument('--cnpj', help='Organization CNPJ (use with --year and --sequential)')
    parser.add_argument('--year', type=int, help='Tender year (use with --cnpj and --sequential)')
    parser.add_argument('--sequential', type=int, help='Tender sequential number (use with --cnpj and --year)')
    parser.add_argument('--download', action='store_true', help='Download document files')
    parser.add_argument('--output', default='tender_documents', help='Output directory')
    parser.add_argument('--documents-only', action='store_true', help='Fetch only documents (skip history and atas)')
    parser.add_argument('--history-only', action='store_true', help='Fetch only history')
    parser.add_argument('--atas-only', action='store_true', help='Fetch only atas')

    args = parser.parse_args()

    # Parse control number OR validate individual components
    if args.control_number:
        # Parse control number
        try:
            cnpj, year, sequential = parse_control_number(args.control_number)
            print(f"📋 Parsed control number: {args.control_number}")
            print(f"   CNPJ: {cnpj}")
            print(f"   Year: {year}")
            print(f"   Sequential: {sequential}\n")
        except ValueError as e:
            print(f"❌ Error: {e}")
            print(f"\nExpected format: CNPJ-1-SEQUENTIAL/YEAR")
            print(f"Example: 46374500000194-1-006949/2025")
            return
    elif args.cnpj and args.year and args.sequential:
        # Use individual components
        cnpj = args.cnpj
        year = args.year
        sequential = args.sequential
    else:
        print("❌ Error: You must provide either:")
        print("  1. --control-number (e.g., '46374500000194-1-006949/2025')")
        print("  OR")
        print("  2. All three: --cnpj, --year, and --sequential")
        print("\nRun with --help for examples.")
        return

    fetcher = TenderDocumentFetcher(output_dir=args.output)

    try:
        if args.documents_only:
            await fetcher.fetch_tender_documents(cnpj, year, sequential, args.download)
        elif args.history_only:
            await fetcher.fetch_tender_history(cnpj, year, sequential)
        elif args.atas_only:
            await fetcher.fetch_tender_atas(cnpj, year, sequential, args.download)
        else:
            # Fetch all
            await fetcher.fetch_all(cnpj, year, sequential, args.download)

    finally:
        await fetcher.close()


if __name__ == "__main__":
    asyncio.run(main())
