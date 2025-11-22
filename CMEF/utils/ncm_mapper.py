"""
NCM Mapper

Maps medical equipment categories to Brazilian NCM (Nomenclatura Comum do Mercosul) codes
and classifies risk levels according to ANVISA regulations.
"""

import logging
from typing import Dict, Optional, Tuple
import json
from pathlib import Path

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import (
    CMEFConfig,
    DEFAULT_CONFIG,
    NCM_CATEGORY_MAPPINGS,
    RISK_CLASSIFICATION_RULES
)

logger = logging.getLogger(__name__)


class NCMMapper:
    """Maps product categories to NCM codes and risk classifications"""

    def __init__(self, config: CMEFConfig = DEFAULT_CONFIG):
        """
        Initialize NCM mapper

        Args:
            config: CMEF configuration object
        """
        self.config = config
        self.ncm_mappings = NCM_CATEGORY_MAPPINGS.copy()
        self.risk_rules = RISK_CLASSIFICATION_RULES.copy()

        # Load custom mappings if available
        self._load_custom_mappings()

        logger.info(f"Initialized NCM mapper with {len(self.ncm_mappings)} category mappings")

    def _load_custom_mappings(self):
        """Load custom NCM mappings from config file if available"""
        mappings_file = self.config.get_full_path(self.config.NCM_MAPPINGS_FILE)

        if Path(mappings_file).exists():
            try:
                with open(mappings_file, 'r', encoding='utf-8') as f:
                    custom_mappings = json.load(f)

                # Update mappings
                self.ncm_mappings.update(custom_mappings.get('ncm_mappings', {}))
                self.risk_rules.update(custom_mappings.get('risk_rules', {}))

                logger.info(f"Loaded custom NCM mappings from {mappings_file}")

            except Exception as e:
                logger.warning(f"Failed to load custom NCM mappings: {e}")

    def get_ncm_code(self, category: str, subcategory: Optional[str] = None) -> str:
        """
        Get NCM code for a product category

        Args:
            category: Primary product category
            subcategory: More specific subcategory (optional)

        Returns:
            NCM code (8-digit format: XXXX.XX.XX)
        """
        # Try subcategory first (more specific)
        if subcategory:
            key = f"{category} - {subcategory}"
            if key in self.ncm_mappings:
                return self.ncm_mappings[key]

            # Try just subcategory
            if subcategory in self.ncm_mappings:
                return self.ncm_mappings[subcategory]

        # Try primary category
        if category in self.ncm_mappings:
            return self.ncm_mappings[category]

        # Fuzzy matching for partial matches
        category_lower = category.lower()
        for key, ncm_code in self.ncm_mappings.items():
            if category_lower in key.lower():
                logger.debug(f"Fuzzy match: '{category}' -> '{key}' ({ncm_code})")
                return ncm_code

        # Default NCM for unclassified medical equipment
        logger.warning(f"No NCM mapping found for category: {category}")
        return "9018.90.99"  # Other medical instruments and appliances

    def classify_risk(
        self,
        category: str,
        scope_description: str
    ) -> Tuple[str, float]:
        """
        Classify medical device risk level (ANVISA)

        Risk Classes:
        - Class I: Low risk (basic equipment, disposables)
        - Class II: Medium risk (diagnostic, surgical tools)
        - Class III: High risk (implants, life-support)

        Args:
            category: Product category
            scope_description: Product description text

        Returns:
            Tuple of (risk_class, confidence)
        """
        scope_lower = scope_description.lower()
        category_lower = category.lower()

        # Check each risk class
        for risk_class in ["III", "II", "I"]:
            keywords = self.risk_rules.get(risk_class, [])

            for keyword in keywords:
                if keyword.lower() in scope_lower or keyword.lower() in category_lower:
                    logger.debug(f"Risk classification: Class {risk_class} (keyword: '{keyword}')")
                    return risk_class, 0.9

        # Default: Class II (medium risk)
        logger.debug(f"Default risk classification: Class II")
        return "II", 0.5

    def enrich_company_data(self, company: Dict) -> Dict:
        """
        Enrich company data with NCM code and risk classification

        Args:
            company: Company data dictionary

        Returns:
            Enriched company data with ncm_code and risk_class fields
        """
        category = company.get('product_category', 'Other Medical Equipment')
        subcategory = company.get('product_subcategory')
        scope = company.get('scope_description', '')

        # Get NCM code
        ncm_code = self.get_ncm_code(category, subcategory)

        # Classify risk
        risk_class, risk_confidence = self.classify_risk(category, scope)

        # Add to company data
        company['ncm_code'] = ncm_code
        company['risk_class'] = risk_class
        company['risk_confidence'] = risk_confidence

        logger.debug(f"Enriched: {company.get('company_name_en', 'Unknown')} -> NCM: {ncm_code}, Risk: Class {risk_class}")

        return company

    def get_ncm_description(self, ncm_code: str) -> str:
        """
        Get human-readable description for NCM code

        Args:
            ncm_code: 8-digit NCM code

        Returns:
            Description of the NCM category
        """
        # Reverse lookup
        for category, code in self.ncm_mappings.items():
            if code == ncm_code:
                return category

        return "Medical Equipment (Unspecified)"

    def validate_ncm_code(self, ncm_code: str) -> bool:
        """
        Validate NCM code format

        Args:
            ncm_code: NCM code to validate

        Returns:
            True if valid format
        """
        import re

        # NCM format: XXXX.XX.XX (8 digits with dots)
        pattern = r'^\d{4}\.\d{2}\.\d{2}$'

        if re.match(pattern, ncm_code):
            return True

        logger.warning(f"Invalid NCM code format: {ncm_code}")
        return False

    def export_mappings(self, output_file: str):
        """
        Export current NCM mappings to JSON file

        Args:
            output_file: Path to output file
        """
        mappings_data = {
            'ncm_mappings': self.ncm_mappings,
            'risk_rules': self.risk_rules
        }

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(mappings_data, f, indent=2, ensure_ascii=False)

        logger.info(f"Exported NCM mappings to {output_file}")


# ==================== STATISTICS & ANALYSIS ====================

class NCMStatistics:
    """Analyze NCM code distribution in dataset"""

    def __init__(self, companies: list):
        """
        Initialize statistics analyzer

        Args:
            companies: List of company dictionaries
        """
        self.companies = companies

    def get_ncm_distribution(self) -> Dict[str, int]:
        """Get distribution of NCM codes"""
        distribution = {}

        for company in self.companies:
            ncm = company.get('ncm_code', 'Unknown')
            distribution[ncm] = distribution.get(ncm, 0) + 1

        return dict(sorted(distribution.items(), key=lambda x: x[1], reverse=True))

    def get_risk_distribution(self) -> Dict[str, int]:
        """Get distribution of risk classes"""
        distribution = {}

        for company in self.companies:
            risk = company.get('risk_class', 'Unknown')
            distribution[risk] = distribution.get(risk, 0) + 1

        return distribution

    def get_category_distribution(self) -> Dict[str, int]:
        """Get distribution of product categories"""
        distribution = {}

        for company in self.companies:
            category = company.get('product_category', 'Unknown')
            distribution[category] = distribution.get(category, 0) + 1

        return dict(sorted(distribution.items(), key=lambda x: x[1], reverse=True))

    def print_summary(self):
        """Print summary statistics"""
        logger.info("\n" + "=" * 70)
        logger.info("NCM & RISK CLASSIFICATION STATISTICS")
        logger.info("=" * 70)

        logger.info(f"\nTotal Companies: {len(self.companies)}")

        # NCM distribution
        logger.info("\nTop 10 NCM Codes:")
        ncm_dist = self.get_ncm_distribution()
        for i, (ncm, count) in enumerate(list(ncm_dist.items())[:10], 1):
            percentage = (count / len(self.companies)) * 100
            logger.info(f"  {i}. {ncm}: {count} ({percentage:.1f}%)")

        # Risk distribution
        logger.info("\nRisk Class Distribution:")
        risk_dist = self.get_risk_distribution()
        for risk_class in ["I", "II", "III", "Unknown"]:
            count = risk_dist.get(risk_class, 0)
            percentage = (count / len(self.companies)) * 100 if self.companies else 0
            logger.info(f"  Class {risk_class}: {count} ({percentage:.1f}%)")

        # Category distribution
        logger.info("\nTop 10 Product Categories:")
        cat_dist = self.get_category_distribution()
        for i, (category, count) in enumerate(list(cat_dist.items())[:10], 1):
            percentage = (count / len(self.companies)) * 100
            logger.info(f"  {i}. {category}: {count} ({percentage:.1f}%)")


__all__ = ['NCMMapper', 'NCMStatistics']
