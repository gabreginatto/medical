"""
AI-Powered Product Matching Module

This module provides AI-powered matching of tender items to product catalogs
using Google Gemini. It uses a two-stage approach:

1. SQL filtering to reduce the search space
2. AI-powered batch matching for intelligent product identification

Usage:
    from ai_matching import extract, match, save, report

    # Run complete workflow
    items = extract.extract_filtered_items()
    matches = match.match_all_items(items)
    save.save_matches_to_database(matches)
    report.generate_matching_report()

Modules:
    - step1_extract: Extract filtered items from database
    - step2_gemini: AI matching using Gemini
    - step3_save: Save results to database
    - step4_report: Generate analysis reports
    - utils: Helper utilities
"""

__version__ = '1.0.0'
__author__ = 'Medical Data Processing Team'

# Import main functions for convenient access
from pathlib import Path

# Module directory
MODULE_DIR = Path(__file__).parent
DATA_DIR = MODULE_DIR.parent / 'data'
DOCS_DIR = MODULE_DIR.parent / 'docs' / 'ai_matching'

# Ensure data directory exists
DATA_DIR.mkdir(exist_ok=True)
