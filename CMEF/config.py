"""
CMEF Catalog Processing Configuration

Configuration for the CMEF catalog extraction, classification, and enrichment pipeline.
"""

import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from pathlib import Path


@dataclass
class CMEFConfig:
    """Configuration for CMEF catalog processing"""

    # ==================== FILE PATHS ====================

    # Input PDF
    PDF_PATH: str = "/Users/gabrielreginatto/Desktop/Code/Medical/CMEF/CMEF_2025.pdf"

    # Base directory
    BASE_DIR: str = "/Users/gabrielreginatto/Desktop/Code/Medical/CMEF"

    # Output directories
    OUTPUT_DIR: str = "data"
    CONFIG_DIR: str = "config"
    LOGS_DIR: str = "logs"

    # ==================== OCR PROCESSING ====================

    # PDF Processing
    PAGES_PER_BATCH: int = 15  # Pages to process per OCR batch
    IMAGE_DPI: int = 300  # DPI for PDF to image conversion
    MAX_IMAGE_SIZE: tuple = (3000, 3000)  # Max width/height in pixels

    # Image Preprocessing (DISABLED - Gemini works better with raw images)
    APPLY_PREPROCESSING: bool = False
    ENHANCE_CONTRAST: bool = False
    DENOISE: bool = False
    SHARPEN: bool = False

    # ==================== DEEPSEEK OCR API ====================

    # GCP Vertex AI Settings
    DEEPSEEK_PROJECT_ID: str = "medical-473219"
    DEEPSEEK_REGION: str = "us-central1"
    DEEPSEEK_ENDPOINT_NAME: str = "deepseek-ocr-endpoint"

    # DeepSeek OCR Model
    DEEPSEEK_MODEL_ID: str = "publishers/deepseek-ai/models/deepseek-ocr-maas"

    # API Settings
    OCR_TIMEOUT: int = 120  # seconds per batch
    OCR_MAX_RETRIES: int = 3
    OCR_RETRY_DELAY: int = 5  # seconds

    # ==================== GEMINI API ====================

    # Model Selection
    GEMINI_MODEL: str = "gemini-2.5-flash"  # Gemini 2.5 Flash (GA)
    GEMINI_FALLBACK_MODEL: str = "gemini-1.5-flash"  # Fallback if 2.5 unavailable

    # Batch Processing
    GEMINI_BATCH_SIZE: int = 20  # Companies to process per API call
    GEMINI_TIMEOUT: int = 60  # seconds
    GEMINI_MAX_RETRIES: int = 3

    # Rate Limiting (Gemini 2.5 Flash free tier: 15 RPM)
    GEMINI_REQUESTS_PER_MINUTE: int = 12  # Conservative: 12 RPM (below 15 limit)
    GEMINI_REQUEST_DELAY: float = 5.0  # 5 seconds between requests (12 per minute)

    # ==================== DATA PARSING ====================

    # Field Extraction Confidence Thresholds
    MIN_CONFIDENCE_SCORE: float = 0.7  # Minimum confidence for AI-extracted fields

    # Website Validation
    VALIDATE_WEBSITES: bool = True
    WEBSITE_TIMEOUT: int = 10  # seconds
    MAX_CONCURRENT_VALIDATIONS: int = 10

    # Email Validation
    VALIDATE_EMAILS: bool = True  # Basic format validation

    # ==================== CLASSIFICATION ====================

    # Risk Classification
    RISK_CLASSES: List[str] = field(default_factory=lambda: ["I", "II", "III", "Unknown"])

    # Product Categories (used by Gemini classification)
    BASE_PRODUCT_CATEGORIES: List[str] = field(default_factory=lambda: [
        "Cardiology & Cardiovascular",
        "Orthopedics & Rehabilitation",
        "Radiology & Imaging Equipment",
        "Surgical Instruments & Tools",
        "Laboratory & Diagnostics",
        "Critical Care & Monitoring",
        "Respiratory Care",
        "Obstetrics & Gynecology",
        "Dentistry & Oral Care",
        "Ophthalmology Equipment",
        "Neurology & Neurosurgery",
        "Hospital Furniture & Infrastructure",
        "Disposable Medical Supplies",
        "Sterilization & Disinfection",
        "Emergency & Rescue Equipment",
        "Other Medical Equipment"
    ])

    # ==================== DATABASE ====================

    # Table name
    DATABASE_TABLE: str = "cmef_companies"

    # Batch insert size
    DB_BATCH_SIZE: int = 100

    # ==================== LOGGING ====================

    LOG_LEVEL: str = "INFO"  # DEBUG, INFO, WARNING, ERROR
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Log files
    OCR_LOG_FILE: str = "logs/ocr_extraction.log"
    PARSING_LOG_FILE: str = "logs/parsing.log"
    CLASSIFICATION_LOG_FILE: str = "logs/classification.log"
    DATABASE_LOG_FILE: str = "logs/database.log"

    # ==================== OUTPUT FILES ====================

    # Step outputs
    OCR_OUTPUT_FILE: str = "data/ocr_raw_output.json"
    STRUCTURED_OUTPUT_FILE: str = "data/structured_companies.json"
    ENRICHED_OUTPUT_FILE: str = "data/enriched_companies.json"

    # Intermediate files
    PDF_IMAGES_DIR: str = "data/pdf_images"
    PREPROCESSED_IMAGES_DIR: str = "data/preprocessed_images"

    # Reports
    VALIDATION_REPORT_FILE: str = "data/validation_report.json"
    STATISTICS_REPORT_FILE: str = "data/statistics_report.json"

    # ==================== NCM CONFIGURATION ====================

    NCM_MAPPINGS_FILE: str = "config/ncm_mappings.json"

    # ==================== METHODS ====================

    def __post_init__(self):
        """Create necessary directories"""
        base_path = Path(self.BASE_DIR)

        # Create output directories
        (base_path / self.OUTPUT_DIR).mkdir(exist_ok=True)
        (base_path / self.CONFIG_DIR).mkdir(exist_ok=True)
        (base_path / self.LOGS_DIR).mkdir(exist_ok=True)
        (base_path / self.PDF_IMAGES_DIR).mkdir(parents=True, exist_ok=True)
        (base_path / self.PREPROCESSED_IMAGES_DIR).mkdir(parents=True, exist_ok=True)

    def get_full_path(self, relative_path: str) -> str:
        """Convert relative path to full path"""
        return str(Path(self.BASE_DIR) / relative_path)

    def get_api_key(self, key_name: str) -> Optional[str]:
        """Get API key from environment"""
        return os.getenv(key_name)


# ==================== REGEX PATTERNS ====================

REGEX_PATTERNS = {
    'email': r'[\w\.\-]+@[\w\.\-]+\.\w+',
    'website': r'(?:www\.|https?://)[^\s,;]+',
    'booth_number': r'\d+\.\d+[A-Z]\d+',
    'chinese_chars': r'[\u4e00-\u9fff]+',
    'phone': r'\+?\d{1,4}[-\s]?\(?\d{1,4}\)?[-\s]?\d{1,4}[-\s]?\d{1,9}',
    'postal_code': r'\d{5,6}'
}


# ==================== RISK CLASSIFICATION RULES ====================

RISK_CLASSIFICATION_RULES = {
    # Class III - High Risk (Implants, Life-supporting equipment)
    "III": [
        "cardiology interventional",
        "cardiac implant",
        "pacemaker",
        "stent",
        "orthopedic implant",
        "joint replacement",
        "spinal implant",
        "neurosurgery",
        "implantable",
        "life support",
        "ventilator",
        "anesthesia machine",
        "dialysis"
    ],

    # Class II - Medium Risk (Diagnostic equipment, surgical tools)
    "II": [
        "diagnostic equipment",
        "imaging",
        "ultrasound",
        "x-ray",
        "mri",
        "ct scanner",
        "surgical instrument",
        "endoscope",
        "patient monitor",
        "infusion pump",
        "surgical laser",
        "sterilization equipment"
    ],

    # Class I - Low Risk (Basic equipment, disposables)
    "I": [
        "disposable",
        "bandage",
        "gauze",
        "syringe",
        "wheelchair",
        "hospital bed",
        "examination table",
        "stethoscope",
        "thermometer",
        "blood pressure cuff",
        "basic surgical tool",
        "hospital furniture"
    ]
}


# ==================== NCM CATEGORY MAPPINGS ====================
# NCM codes for medical equipment categories (Brazilian tax classification)

NCM_CATEGORY_MAPPINGS = {
    "Cardiology": "9018.19.80",  # Electrocardiographs and other cardiology instruments
    "Cardiology Interventional": "9021.31.10",  # Artificial joints and other orthopedic appliances
    "Orthopedic Implants": "9021.10.10",  # Orthopedic or fracture appliances
    "Orthopedics": "9021.10.20",  # Other orthopedic appliances
    "Imaging Equipment - X-Ray": "9022.12.00",  # Apparatus based on X-rays - computed tomography
    "Imaging Equipment - Ultrasound": "9018.12.10",  # Ultrasonic scanning apparatus
    "Imaging Equipment - MRI": "9018.13.00",  # Magnetic resonance imaging apparatus
    "Surgical Instruments": "9018.90.95",  # Other instruments and appliances
    "Surgical Laser": "9018.20.00",  # Ultraviolet or infrared ray apparatus
    "Diagnostics - Lab": "9027.80.90",  # Other instruments for physical or chemical analysis
    "Patient Monitoring": "9018.19.10",  # Electro-diagnostic apparatus
    "Infusion Pump": "9018.31.00",  # Syringes with or without needles
    "Ventilator": "9019.20.00",  # Ozone, oxygen, aerosol therapy apparatus
    "Anesthesia": "9018.90.50",  # Anesthetic apparatus and instruments
    "Dialysis": "9018.90.11",  # Apparatus for hemodialysis
    "Sterilization": "8419.20.00",  # Medical, surgical or laboratory sterilizers
    "Hospital Furniture": "9402.90.00",  # Other medical, surgical or dental furniture
    "Wheelchairs": "8713.10.00",  # Wheelchairs not mechanically propelled
    "Disposable Supplies": "9018.90.99",  # Other instruments and appliances
    "Endoscopy": "9018.11.00",  # Electro-cardiographs
    "Laboratory Equipment": "9027.90.90",  # Parts and accessories of lab equipment
    "Dental Equipment": "9018.49.00",  # Other dental instruments
    "Ophthalmology": "9018.50.90",  # Other ophthalmic instruments
}


# ==================== DEFAULT CONFIGURATION INSTANCE ====================

DEFAULT_CONFIG = CMEFConfig()


# ==================== EXPORTS ====================

__all__ = [
    'CMEFConfig',
    'DEFAULT_CONFIG',
    'REGEX_PATTERNS',
    'RISK_CLASSIFICATION_RULES',
    'NCM_CATEGORY_MAPPINGS'
]
