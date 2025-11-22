"""
CMEF Catalog Processing Module

This module processes the CMEF (China Medical Equipment Fair) catalog PDF
to extract, classify, and enrich medical equipment manufacturer data.

Workflow:
1. OCR Extraction (DeepSeek) - Convert PDF images to text
2. Parsing & Structuring (Gemini) - Extract structured company data
3. Classification & Enrichment - Add NCM codes and risk classifications
4. Database Integration - Save to PostgreSQL for analysis

Author: Medical PNCP Integration System
"""

__version__ = "1.0.0"
__all__ = [
    "CMEFConfig",
    "step1_ocr_extraction",
    "step2_parse_and_structure",
    "step3_classify_enrich",
    "step4_save_database"
]
