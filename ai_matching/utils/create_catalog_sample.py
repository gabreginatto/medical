#!/usr/bin/env python3
"""
Helper script: Create sample Fernandes product catalog
This is a template - replace with your actual Fernandes product data
"""

import json
import os


def create_sample_catalog():
    """Create sample Fernandes product catalog"""

    # Sample Fernandes products - REPLACE WITH YOUR ACTUAL DATA
    sample_products = [
        {
            "code": "FT1012",
            "name": "Filme Transparente Tegaderm 10x12cm",
            "price": 4.50,
            "category": "Curativos Transparentes",
            "description": "Curativo adesivo transparente estéril 10x12cm"
        },
        {
            "code": "FT0610",
            "name": "Filme Transparente Tegaderm 6x10cm",
            "price": 3.20,
            "category": "Curativos Transparentes",
            "description": "Curativo adesivo transparente estéril 6x10cm"
        },
        {
            "code": "CH1010",
            "name": "Curativo Hidrocoloide 10x10cm",
            "price": 8.90,
            "category": "Curativos Hidrocoloides",
            "description": "Curativo hidrocoloide adesivo 10x10cm"
        },
        {
            "code": "CH1515",
            "name": "Curativo Hidrocoloide 15x15cm",
            "price": 12.50,
            "category": "Curativos Hidrocoloides",
            "description": "Curativo hidrocoloide adesivo 15x15cm"
        },
        {
            "code": "GE1010",
            "name": "Gaze Estéril 10x10cm",
            "price": 0.45,
            "category": "Gazes",
            "description": "Gaze estéril 100% algodão 10x10cm"
        },
        {
            "code": "AT10CM",
            "name": "Atadura Crepe 10cm",
            "price": 1.80,
            "category": "Ataduras",
            "description": "Atadura de crepe 10cm x 4.5m"
        },
        {
            "code": "AT15CM",
            "name": "Atadura Crepe 15cm",
            "price": 2.20,
            "category": "Ataduras",
            "description": "Atadura de crepe 15cm x 4.5m"
        },
        {
            "code": "ESP5CM",
            "name": "Esparadrapo 5cm",
            "price": 3.50,
            "category": "Fixação",
            "description": "Esparadrapo impermeável 5cm x 4.5m"
        },
        {
            "code": "CC1010",
            "name": "Compressa Cirúrgica 10x10cm",
            "price": 0.60,
            "category": "Compressas",
            "description": "Compressa de gaze estéril 10x10cm"
        },
        {
            "code": "BA7519",
            "name": "Band-Aid Transparente 75x19mm",
            "price": 0.25,
            "category": "Band-Aids",
            "description": "Band-aid adesivo transparente 75x19mm"
        }
    ]

    # Create data directory
    os.makedirs('data', exist_ok=True)

    # Save to JSON
    catalog_data = {
        "catalog_name": "Fernandes Medical Products",
        "version": "1.0",
        "created_at": "2025-01-01",
        "total_products": len(sample_products),
        "products": sample_products
    }

    output_file = 'config/fernandes_products.json'

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(catalog_data, f, indent=2, ensure_ascii=False)

    print("=" * 70)
    print("📦 SAMPLE FERNANDES CATALOG CREATED")
    print("=" * 70)
    print(f"File: {output_file}")
    print(f"Products: {len(sample_products)}")
    print()
    print("⚠️  THIS IS A SAMPLE CATALOG")
    print("   Replace with your actual Fernandes product data!")
    print()
    print("Expected format:")
    print("  - code: Product code/SKU")
    print("  - name: Product name")
    print("  - price: Price in BRL")
    print("  - category: Product category (optional)")
    print("  - description: Full description (optional)")
    print("=" * 70)


if __name__ == "__main__":
    create_sample_catalog()
