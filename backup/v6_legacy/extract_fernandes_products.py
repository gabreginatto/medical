#!/usr/bin/env python3
"""
Extract Fernandes product list from PDF to CSV
"""

import PyPDF2
import re
import csv
import json

def extract_products_from_pdf(pdf_path):
    """Extract product data from Fernandes PDF"""

    products = []

    with open(pdf_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)

        # Extract all text
        all_text = ""
        for page in reader.pages:
            all_text += page.extract_text()

        # Pattern: number + code + description
        # e.g., "1 IVFS.5057CURATIVO IV..."
        pattern = r'(\d+)\s+([A-Z]+[\w.]+?)([A-Z]{2,}.*?)(?=\d+\s+[A-Z]+[\w.]+?[A-Z]{2,}|$)'

        matches = re.findall(pattern, all_text, re.DOTALL)

        for match in matches:
            num, code, rest = match

            # Extract price and MOQ from rest
            price_match = re.search(r'(\d+\.\d{4})\s+(\d+)\s*$', rest)

            if price_match:
                # Remove price/MOQ from description
                description = rest[:price_match.start()].strip()

                # Clean up description - remove photo codes and packaging info
                description = re.sub(r'HR\d+.*?(?=[A-Z]|$)', '', description)
                description = re.sub(r'HM\d+.*?(?=[A-Z]|$)', '', description)
                description = re.sub(r'\d+\s*pouches/box.*?carton', '', description)
                description = re.sub(r'\d+cm\*\d+cm', '', description)
                description = re.sub(r'/[\d.]+cm.*?(?=[A-Z]|$)', '', description)
                description = re.sub(r'\s+', ' ', description).strip()

                products.append({
                    'CÓDIGO': code,
                    'DESCRIÇÃO': description,
                    'FOB NINGBO USD/unit': float(price_match.group(1)),
                    'MOQ/unit': int(price_match.group(2))
                })

    return products

def save_to_csv(products, output_path):
    """Save products to CSV file"""

    if not products:
        print("No products to save")
        return

    fieldnames = ['CÓDIGO', 'DESCRIÇÃO', 'FOB NINGBO USD/unit', 'MOQ/unit']

    with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for product in products:
            writer.writerow(product)

    print(f"✅ Saved {len(products)} products to {output_path}")

def main():
    pdf_path = 'Docs/Fernandes-price-20250805 (1).pdf'
    csv_path = 'fernandes_products.csv'
    json_path = 'fernandes_products.json'

    print("📄 Extracting products from PDF...")
    products = extract_products_from_pdf(pdf_path)

    print(f"✅ Extracted {len(products)} products")

    # Show first 3 products as sample
    print("\n=== SAMPLE PRODUCTS ===")
    for i, prod in enumerate(products[:3], 1):
        print(f"\n{i}. {prod.get('CÓDIGO', 'N/A')}")
        print(f"   Description: {prod.get('DESCRIÇÃO', 'N/A')[:80]}...")
        print(f"   FOB Price: ${prod.get('FOB NINGBO USD/unit', 'N/A')}")
        print(f"   MOQ: {prod.get('MOQ/unit', 'N/A')}")

    # Save to CSV
    save_to_csv(products, csv_path)

    # Save to JSON for easier loading
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(products, f, indent=2, ensure_ascii=False)
    print(f"✅ Saved to {json_path}")

    print(f"\n📊 Total products extracted: {len(products)}")

if __name__ == "__main__":
    main()
