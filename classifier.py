"""
Tender Classification System for PNCP Data
Classifies tenders by government level, size, organization type, and relevance to medical supplies
"""

import re
import logging
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass
from config import (
    GovernmentLevel, TenderSize, OrganizationType,
    classify_tender_size, CONTRACTING_MODALITIES, BRAZILIAN_STATES
)

logger = logging.getLogger(__name__)

@dataclass
class ClassificationResult:
    """Result of tender classification"""
    # Location information
    state_code: Optional[str]
    state_name: Optional[str]
    city: Optional[str]

    # Government classification
    government_level: GovernmentLevel
    government_level_confidence: float

    # Organization classification
    organization_type: OrganizationType
    organization_type_confidence: float

    # Structured API data
    contracting_modality_id: Optional[int]
    contracting_modality_name: Optional[str]
    is_material: Optional[bool]  # True if materialOuServico="M"

    # Size and relevance
    tender_size: TenderSize
    is_medical_relevant: bool
    medical_relevance_score: float
    medical_keywords_found: List[str]
    reasoning: str

class TenderClassifier:
    """Classifies tenders based on organization data and tender content"""

    def __init__(self):
        # Keywords for government level classification
        self.federal_keywords = {
            # Federal ministries and agencies
            'ministério', 'ministry', 'governo federal', 'federal government',
            'união', 'union', 'presidente da república', 'presidência',
            # Health agencies
            'anvisa', 'agência nacional de vigilância sanitária',
            'sus', 'sistema único de saúde',
            'ministério da saúde', 'ministry of health',
            'fiocruz', 'fundação oswaldo cruz',
            'inca', 'instituto nacional do câncer',
            'funasa', 'fundação nacional de saúde',
            'hemobrás', 'empresa brasileira de hemoderivados',
            # Federal hospitals
            'hospital federal', 'instituto nacional', 'centro nacional',
            # Federal universities with hospitals
            'universidade federal', 'hospital universitário federal',
            'hospital de clínicas federal'
        }

        self.state_keywords = {
            # State government indicators
            'governo do estado', 'state government', 'secretaria de estado',
            'estado de', 'state of', 'governo estadual', 'state government',
            # State health secretariats
            'secretaria estadual de saúde', 'secretaria de saúde do estado',
            'ses', 'saúde estadual', 'state health',
            # State hospitals
            'hospital do estado', 'state hospital', 'hospital estadual',
            'centro estadual', 'instituto estadual',
            # State universities
            'universidade estadual', 'state university',
            'hospital universitário estadual'
        }

        self.municipal_keywords = {
            # Municipal government indicators
            'município', 'municipality', 'prefeitura', 'city hall',
            'câmara municipal', 'city council', 'governo municipal',
            # Municipal health
            'secretaria municipal de saúde', 'secretaria de saúde municipal',
            'sms', 'saúde municipal', 'municipal health',
            # Municipal health facilities
            'hospital municipal', 'municipal hospital',
            'upa', 'unidade de pronto atendimento',
            'posto de saúde', 'health center',
            'centro de saúde municipal', 'municipal health center',
            'policlínica municipal', 'municipal polyclinic'
        }

        # Keywords for organization type classification
        self.hospital_keywords = {
            'hospital', 'hospital', 'nosocomial', 'hospitalar',
            'clínica', 'clinic', 'clinica', 'clinical',
            'maternidade', 'maternity', 'maternidad',
            'santa casa', 'irmandade', 'brotherhood',
            'instituto do coração', 'heart institute',
            'instituto do câncer', 'cancer institute',
            'centro médico', 'medical center',
            'complexo hospitalar', 'hospital complex',
            'hospital de base', 'base hospital',
            'hospital regional', 'regional hospital'
        }

        self.health_secretariat_keywords = {
            'secretaria de saúde', 'health secretariat',
            'secretaria da saúde', 'department of health',
            'vigilância sanitária', 'health surveillance',
            'vigilância epidemiológica', 'epidemiological surveillance',
            'centro de controle', 'control center',
            'fundação de saúde', 'health foundation'
        }

        self.university_keywords = {
            'universidade', 'university', 'universidad',
            'faculdade', 'faculty', 'college',
            'instituto federal', 'federal institute',
            'centro universitário', 'university center',
            'escola superior', 'higher school'
        }

        self.military_keywords = {
            'exército', 'army', 'marinha', 'navy',
            'aeronáutica', 'air force', 'militar', 'military',
            'comando', 'command', 'quartel', 'barracks',
            'hospital militar', 'military hospital',
            'policlínica militar', 'military polyclinic'
        }

        # Enhanced medical relevance keywords (organized by category)
        self.medical_keywords = {
            # Wound care and dressings (Fernandes core products)
            'curativo', 'bandage', 'dressing', 'atadura', 'bandagem',
            'gaze', 'gauze', 'compressa', 'compress',
            'esparadrapo', 'tape', 'fita adesiva', 'adhesive tape',
            'filme transparente', 'transparent film', 'hidrocolóide', 'hydrocolloid',
            'alginato', 'alginate', 'espuma', 'foam dressing',
            'borda adesiva', 'adhesive border', 'fenestrado', 'fenestrated',

            # IV products and vascular access (Fernandes products)
            'cateter', 'catheter', 'cateter iv', 'iv catheter',
            'scalp', 'jelco', 'agulha', 'needle',
            'equipo', 'infusion set', 'soro', 'saline',
            'acesso venoso', 'venous access', 'punção', 'puncture',
            'fixação iv', 'iv fixation', 'stabilização', 'stabilization',

            # Surgical supplies
            'cirúrgico', 'surgical', 'cirurgia', 'surgery',
            'campo cirúrgico', 'surgical drape', 'avental cirúrgico', 'surgical gown',
            'luva cirúrgica', 'surgical glove', 'máscara cirúrgica', 'surgical mask',
            'capote', 'gown', 'propé', 'shoe cover',
            'bisturi', 'scalpel', 'pinça', 'forceps',
            'tesoura cirúrgica', 'surgical scissors',

            # Sterile and disposable supplies
            'estéril', 'sterile', 'esterilização', 'sterilization',
            'descartável', 'disposable', 'uso único', 'single use',
            'antisséptico', 'antiseptic', 'asséptico', 'aseptic',
            'autoclavável', 'autoclavable',

            # Medical supplies (general)
            'seringa', 'syringe', 'algodão', 'cotton',
            'luva', 'glove', 'máscara', 'mask',
            'avental', 'gown', 'touca', 'cap',
            'sonda', 'probe', 'tubo', 'tube',
            'dreno', 'drain', 'cânula', 'cannula',

            # Medical equipment categories
            'equipamento médico', 'medical equipment',
            'aparelho médico', 'medical device',
            'instrumental médico', 'medical instruments',
            'material médico', 'medical materials',
            'insumo médico', 'medical supplies',
            'material hospitalar', 'hospital materials',
            'material de consumo', 'consumable materials',

            # Monitoring and diagnostics
            'monitor', 'oxímetro', 'oximeter',
            'termômetro', 'thermometer', 'esfigmomanômetro', 'sphygmomanometer',
            'estetoscópio', 'stethoscope',

            # Imaging equipment
            'raio-x', 'x-ray', 'ultrassom', 'ultrasound',
            'tomografia', 'tomography', 'ressonância', 'resonance',

            # Laboratory
            'laboratório', 'laboratory', 'análise clínica', 'clinical analysis',
            'coleta', 'collection', 'reagente', 'reagent',
            'vidraria', 'glassware', 'pipeta', 'pipette',

            # Wound and skin care
            'ferida', 'wound', 'lesão', 'lesion',
            'úlcera', 'ulcer', 'queimadura', 'burn',
            'cicatrização', 'healing', 'desbridamento', 'debridement',
            'tratamento de feridas', 'wound treatment',

            # Medical procedures
            'tratamento', 'treatment', 'terapia', 'therapy',
            'procedimento', 'procedure', 'intervenção', 'intervention',
            'assepsia', 'asepsis', 'antissepsia', 'antisepsis',

            # Medical specialties and departments
            'cardiologia', 'cardiology', 'oncologia', 'oncology',
            'pediatria', 'pediatrics', 'ginecologia', 'gynecology',
            'emergência', 'emergency', 'pronto-socorro', 'emergency room',
            'uti', 'icu', 'unidade de terapia intensiva', 'intensive care',
            'centro cirúrgico', 'surgical center', 'bloco cirúrgico', 'operating room',
            'enfermaria', 'ward', 'ambulatório', 'outpatient',

            # Health context
            'saúde', 'health', 'medicina', 'medicine',
            'enfermagem', 'nursing', 'farmácia', 'pharmacy',
            'diagnóstico', 'diagnosis', 'paciente', 'patient',
            'hospitalar', 'hospital', 'clínico', 'clinical'
        }

        # High-relevance keywords (Fernandes-specific products - strongest indicators)
        self.high_relevance_keywords = {
            # Transparent dressings (core Fernandes product line)
            'curativo transparente', 'transparent dressing', 'filme transparente',
            'curativo iv', 'iv dressing', 'fixação iv',
            'fenestrado', 'fenestrated', 'borda adesiva', 'adhesive border',
            'protectfilm', 'protect film',

            # IV and catheter products
            'cateter iv', 'iv catheter', 'cateter intravenoso',
            'scalp', 'jelco', 'acesso venoso', 'fixação de cateter',
            'estabilização', 'stabilization',

            # Wound care specifics
            'curativo estéril', 'sterile dressing',
            'curativo cirúrgico', 'surgical dressing',
            'curativo com borda', 'bordered dressing',
            'filme de poliuretano', 'polyurethane film',

            # Product characteristics
            'hipoalergênico', 'hypoallergenic',
            'impermeável', 'waterproof', 'permeável', 'breathable',
            'não aderente', 'non-adherent',

            # Key terms
            'curativo', 'dressing', 'bandagem', 'bandage',
            'iv', 'intravenoso', 'intravenous',
            'transparente', 'transparent',
            'adesivo', 'adhesive',
            'cirúrgico', 'surgical',
            'estéril', 'sterile'
        }

        # CATMAT medical groups (Brazilian federal supply classification)
        # Group 65: Medical, Dental & Veterinary Equipment and Supplies
        self.catmat_medical_groups = {
            '65': 'Medical, Dental & Veterinary Equipment (All)',
            '6505': 'Drugs and Biologicals',
            '6510': 'Surgical Dressing Materials',
            '6515': 'Medical & Surgical Instruments, Equipment, and Supplies',
            '6520': 'Dental Instruments, Equipment, and Supplies',
            '6525': 'X-Ray Equipment and Supplies: Medical, Dental, Veterinary',
            '6530': 'Hospital Furniture, Equipment, Utensils, and Supplies',
            '6532': 'Hospital and Surgical Clothing and Related Special Purpose Items',
            '6540': 'Ophthalmic Instruments, Equipment, and Supplies',
            '6545': 'Medical Sets, Kits, and Outfits'
        }

        # Detailed CATMAT subcategories for precise matching
        self.catmat_subcategories = {
            # Most relevant for Fernandes products
            '651510': 'Surgical Dressings',
            '651515': 'Adhesive Tapes, Surgical and Medical',
            '651520': 'Bandages and Gauze',
            '651525': 'Wound Care Supplies',
            '651530': 'IV Products and Catheters',
            '651535': 'Syringes and Needles',
            '651540': 'Medical Tubing and Accessories',
            '653205': 'Surgical Gowns, Masks, and Drapes',
            '653210': 'Surgical Gloves and Protective Equipment'
        }

    def extract_catmat_codes(self, text: str) -> List[str]:
        """
        Extract CATMAT codes from tender/item descriptions
        CATMAT codes appear in various formats in Brazilian tenders
        """
        if not text:
            return []

        codes = set()

        # Pattern 1: Explicit CATMAT references
        # Examples: "CATMAT: 6515", "CATMAT 651510", "CATMAT:6515"
        pattern1 = re.findall(r'CATMAT[\s:]*(\d{4,8})', text, re.IGNORECASE)
        codes.update(pattern1)

        # Pattern 2: BR codes (common in Brazilian catalogs)
        # Examples: "BR 0439626", "BR0439626"
        pattern2 = re.findall(r'BR[\s]*(\d{7,})', text, re.IGNORECASE)
        codes.update(pattern2)

        # Pattern 3: Classification codes
        # Examples: "CÓDIGO 6515", "Classe: 651510"
        pattern3 = re.findall(r'(?:CÓDIGO|CLASS[EF]|CLASSIFICAÇÃO)[\s:]*(\d{4,8})', text, re.IGNORECASE)
        codes.update(pattern3)

        # Pattern 4: Standalone 4-6 digit codes starting with 65
        # Examples: "6515", "651510" (medical group indicators)
        pattern4 = re.findall(r'\b(65\d{2,6})\b', text)
        codes.update(pattern4)

        return sorted(list(codes))

    def is_medical_catmat(self, code: str) -> bool:
        """
        Check if CATMAT code belongs to medical group (Group 65)
        Returns True for any code starting with 65
        """
        if not code:
            return False
        return code.startswith('65')

    def get_catmat_category_info(self, code: str) -> Optional[str]:
        """Get category description for a CATMAT code"""
        if not code:
            return None

        # Try exact match in subcategories first
        if code in self.catmat_subcategories:
            return self.catmat_subcategories[code]

        # Try exact match in main groups
        if code in self.catmat_medical_groups:
            return self.catmat_medical_groups[code]

        # Try partial match (e.g., '6515' matches '651510')
        for length in [6, 4, 2]:
            if len(code) >= length:
                prefix = code[:length]
                if prefix in self.catmat_subcategories:
                    return self.catmat_subcategories[prefix]
                if prefix in self.catmat_medical_groups:
                    return self.catmat_medical_groups[prefix]

        return None

    def quick_medical_score(self, tender_data: Dict, org_cache=None) -> Tuple[int, bool]:
        """
        Fast medical scoring without API calls (for Stage 2 quick filtering)
        Returns: (score, should_reject)
        - score: 0-100 confidence score
        - should_reject: True if definitively non-medical
        """
        score = 0
        should_reject = False

        # Extract basic data
        cnpj = tender_data.get('cnpj', '')
        org_name = tender_data.get('orgaoEntidade', {}).get('razaoSocial', '') or tender_data.get('organization_name', '')
        objeto = tender_data.get('objetoCompra', '') or tender_data.get('title', '')

        # Check org cache first (fastest)
        if org_cache and cnpj:
            cache_result = org_cache.is_cached_medical_org(cnpj)
            if cache_result:
                is_medical, confidence = cache_result
                if is_medical:
                    return (int(confidence), False)  # High score, don't reject
                else:
                    return (0, True)  # Reject immediately

        org_name_lower = org_name.lower()
        objeto_lower = objeto.lower()

        # REJECTION KEYWORDS - definitively non-medical
        rejection_keywords = [
            'educacao', 'educação', 'escola', 'ensino',
            'transporte', 'onibus', 'ônibus', 'veiculo', 'veículo',
            'obras', 'pavimentacao', 'pavimentação', 'asfalto',
            'saneamento', 'esgoto', 'água', 'agua',
            'iluminacao', 'iluminação', 'luminaria', 'luminária',
            'informatica', 'informática', 'computador', 'notebook',
            'mobiliario escolar', 'mobiliário escolar',
            'merenda', 'alimentacao escolar', 'alimentação escolar',
            'uniforme escolar', 'fardamento',
            'combustivel', 'combustível', 'gasolina', 'diesel',
            'material de limpeza', 'produto de limpeza'
        ]

        # Check rejection in org name
        for keyword in rejection_keywords:
            if keyword in org_name_lower:
                should_reject = True
                return (0, should_reject)

        # Check rejection in object (less strict)
        rejection_in_object = sum(1 for kw in rejection_keywords if kw in objeto_lower)
        if rejection_in_object >= 2:  # Multiple rejection keywords
            should_reject = True
            return (0, should_reject)

        # MEDICAL ORGANIZATION KEYWORDS
        medical_org_keywords = {
            'hospital': 30,
            'saude': 25,
            'saúde': 25,
            'sus': 20,
            'clinica': 20,
            'clínica': 20,
            'santa casa': 25,
            'upa': 20,
            'samu': 20,
            'hemocentro': 25,
            'hemoderivados': 25,
            'maternidade': 20,
            'policlinica': 20,
            'policlínica': 20,
            'pronto socorro': 20,
            'pronto-socorro': 20,
            'ambulatorio': 15,
            'ambulatório': 15,
            'posto de saude': 15,
            'posto de saúde': 15,
            'vigilancia sanitaria': 20,
            'vigilância sanitária': 20
        }

        for keyword, points in medical_org_keywords.items():
            if keyword in org_name_lower:
                score += points

        # MEDICAL OBJECT KEYWORDS
        medical_object_keywords = {
            'medicamento': 25,
            'medico': 20,
            'médico': 20,
            'hospitalar': 20,
            'cirurgico': 20,
            'cirúrgico': 20,
            'laboratorio': 15,
            'laboratório': 15,
            'curativo': 25,
            'seringa': 20,
            'cateter': 20,
            'equipo': 20,
            'material penso': 20,
            'material médico': 25,
            'material hospitalar': 25,
            'insumo médico': 20,
            'equipamento médico': 20,
            'gaze': 15,
            'luva': 10,
            'máscara': 10,
            'mascara': 10
        }

        for keyword, points in medical_object_keywords.items():
            if keyword in objeto_lower:
                score += points

        # VALUE-BASED ADJUSTMENTS
        homologated_value = tender_data.get('valorTotalHomologado', 0) or 0
        if homologated_value > 50_000:
            score += 10  # Large purchases more likely to be equipment
        elif homologated_value > 100_000:
            score += 15

        # MODALITY CHECK
        modalidade = tender_data.get('modalidadeId')
        if modalidade in [6, 8]:  # Pregão Eletrônico, Dispensa
            score += 5

        return (min(score, 100), should_reject)

    def assess_catmat_relevance(self, text: str) -> Tuple[bool, float, List[str], str]:
        """
        Assess medical relevance using CATMAT codes (post-processing)
        Returns: (is_medical, confidence_score, codes_found, reasoning)
        """
        codes = self.extract_catmat_codes(text)

        if not codes:
            return False, 0.0, [], "No CATMAT codes found"

        # Check if any codes are medical
        medical_codes = [code for code in codes if self.is_medical_catmat(code)]

        if not medical_codes:
            return False, 0.0, codes, f"Non-medical CATMAT codes found: {codes}"

        # High confidence with explicit medical CATMAT codes
        confidence = 95.0

        # Get category descriptions
        categories = []
        for code in medical_codes:
            category = self.get_catmat_category_info(code)
            if category:
                categories.append(f"{code}={category}")

        reasoning = f"Medical CATMAT codes found: {', '.join(categories or medical_codes)}"

        return True, confidence, medical_codes, reasoning

    def _calculate_keyword_score(self, text: str, keywords: Set[str]) -> Tuple[float, List[str]]:
        """Calculate keyword matching score and return found keywords"""
        if not text:
            return 0.0, []

        text_lower = text.lower()
        found_keywords = []

        for keyword in keywords:
            if keyword in text_lower:
                found_keywords.append(keyword)

        # Score based on number of unique keywords found
        score = min(len(found_keywords) / len(keywords) * 100, 100)
        return score, found_keywords

    def classify_government_level(self, cnpj: str, org_name: str,
                                tender_title: str = "", tender_description: str = "",
                                structured_data: Dict = None) -> Tuple[GovernmentLevel, float, str]:
        """Classify government level using structured data and keyword analysis"""

        # First try to use structured API data if available
        if structured_data:
            # Check if organization has sphere indicators from API
            if structured_data.get('esferaFederal'):
                return GovernmentLevel.FEDERAL, 95.0, "API data indicates federal sphere"
            elif structured_data.get('esferaEstadual'):
                return GovernmentLevel.STATE, 95.0, "API data indicates state sphere"
            elif structured_data.get('esferaMunicipal'):
                return GovernmentLevel.MUNICIPAL, 95.0, "API data indicates municipal sphere"
            elif structured_data.get('esferaDistrital'):
                return GovernmentLevel.FEDERAL, 90.0, "API data indicates district sphere (federal)"

        # Fall back to keyword analysis
        combined_text = f"{org_name} {tender_title} {tender_description}".lower()

        # Calculate scores for each level
        federal_score, federal_keywords = self._calculate_keyword_score(combined_text, self.federal_keywords)
        state_score, state_keywords = self._calculate_keyword_score(combined_text, self.state_keywords)
        municipal_score, municipal_keywords = self._calculate_keyword_score(combined_text, self.municipal_keywords)

        # CNPJ-based rules (simplified - would need more sophisticated logic in practice)
        cnpj_boost = 0
        if cnpj and len(cnpj) >= 14:
            # Federal government CNPJs often start with certain patterns
            if cnpj.startswith(('26', '00', '34')):  # Common federal patterns
                federal_score += 20
                cnpj_boost = 20

        # Determine classification
        max_score = max(federal_score, state_score, municipal_score)

        reasoning_parts = []

        if max_score < 10:  # Very low confidence
            return GovernmentLevel.UNKNOWN, max_score, "Insufficient keywords to determine government level"

        if federal_score == max_score:
            level = GovernmentLevel.FEDERAL
            reasoning_parts.append(f"Federal keywords: {federal_keywords[:3]}")
            if cnpj_boost > 0:
                reasoning_parts.append(f"CNPJ pattern suggests federal (+{cnpj_boost}%)")
        elif state_score == max_score:
            level = GovernmentLevel.STATE
            reasoning_parts.append(f"State keywords: {state_keywords[:3]}")
        else:
            level = GovernmentLevel.MUNICIPAL
            reasoning_parts.append(f"Municipal keywords: {municipal_keywords[:3]}")

        reasoning = "; ".join(reasoning_parts)
        confidence = min(max_score, 95)  # Cap at 95% to account for uncertainty

        return level, confidence, reasoning

    def classify_organization_type(self, org_name: str, tender_title: str = "",
                                 tender_description: str = "", structured_data: Dict = None) -> Tuple[OrganizationType, float, str]:
        """Classify organization type using structured data and keyword analysis"""

        combined_text = f"{org_name} {tender_title} {tender_description}".lower()

        # Calculate scores for each type
        scores = {}
        keywords_found = {}

        scores['hospital'], keywords_found['hospital'] = self._calculate_keyword_score(
            combined_text, self.hospital_keywords)
        scores['health_secretariat'], keywords_found['health_secretariat'] = self._calculate_keyword_score(
            combined_text, self.health_secretariat_keywords)
        scores['university'], keywords_found['university'] = self._calculate_keyword_score(
            combined_text, self.university_keywords)
        scores['military'], keywords_found['military'] = self._calculate_keyword_score(
            combined_text, self.military_keywords)

        # Find best match
        best_type = max(scores.keys(), key=lambda k: scores[k])
        max_score = scores[best_type]

        if max_score < 10:
            return OrganizationType.OTHER, max_score, "No specific organization type keywords found"

        # Map to enum
        type_mapping = {
            'hospital': OrganizationType.HOSPITAL,
            'health_secretariat': OrganizationType.HEALTH_SECRETARIAT,
            'university': OrganizationType.UNIVERSITY,
            'military': OrganizationType.MILITARY
        }

        org_type = type_mapping.get(best_type, OrganizationType.OTHER)
        confidence = min(max_score, 90)
        reasoning = f"Keywords found: {keywords_found[best_type][:3]}"

        return org_type, confidence, reasoning

    def assess_medical_relevance(self, tender_title: str, tender_description: str,
                               items_description: str = "") -> Tuple[bool, float, List[str], str]:
        """
        Assess if tender is relevant to medical supplies
        Uses multi-level approach: CATMAT codes (highest confidence) + keywords
        """

        combined_text = f"{tender_title} {tender_description} {items_description}"

        # Level 1: Check for CATMAT codes (highest confidence)
        has_catmat, catmat_confidence, catmat_codes, catmat_reasoning = self.assess_catmat_relevance(combined_text)

        if has_catmat:
            # CATMAT codes provide highest confidence
            return True, catmat_confidence, catmat_codes, catmat_reasoning

        # Level 2: Keyword-based classification (fallback)
        combined_text_lower = combined_text.lower()

        # Calculate general medical relevance
        medical_score, medical_keywords_found = self._calculate_keyword_score(combined_text_lower, self.medical_keywords)

        # Calculate high-relevance score (for products we specifically sell)
        high_rel_score, high_rel_keywords = self._calculate_keyword_score(combined_text_lower, self.high_relevance_keywords)

        # Combined score with weight on high-relevance keywords
        combined_score = (medical_score * 0.6) + (high_rel_score * 0.4)

        # Determine relevance
        is_relevant = combined_score >= 15 or high_rel_score >= 10

        all_keywords_found = list(set(medical_keywords_found + high_rel_keywords))

        reasoning_parts = []
        if high_rel_keywords:
            reasoning_parts.append(f"High-relevance keywords: {high_rel_keywords[:3]}")
        if medical_keywords_found:
            reasoning_parts.append(f"Medical keywords: {medical_keywords_found[:5]}")

        reasoning = "; ".join(reasoning_parts) if reasoning_parts else "No significant medical keywords found"

        return is_relevant, combined_score, all_keywords_found, reasoning

    def extract_location_info(self, tender_data: Dict) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """Extract state, state name, and city from tender data"""

        # Try to get location from structured API fields
        state_code = None
        city = None

        # Look for organization address info
        org_data = tender_data.get('orgao', {})
        if isinstance(org_data, dict):
            # Check for address fields
            endereco = org_data.get('endereco', {})
            if isinstance(endereco, dict):
                state_code = endereco.get('uf') or endereco.get('estado')
                city = endereco.get('municipio') or endereco.get('cidade')

        # Also check top-level fields
        if not state_code:
            state_code = tender_data.get('uf') or tender_data.get('estado')
        if not city:
            city = tender_data.get('municipio') or tender_data.get('cidade')

        # If still no state, try to infer from organization name or CNPJ patterns
        if not state_code:
            org_name = tender_data.get('organization_name', '') or tender_data.get('razaoSocial', '')
            state_code = self._infer_state_from_text(org_name)

        # Get state name from code
        state_name = None
        if state_code and state_code.upper() in BRAZILIAN_STATES:
            state_name = BRAZILIAN_STATES[state_code.upper()]
            state_code = state_code.upper()

        return state_code, state_name, city

    def _infer_state_from_text(self, text: str) -> Optional[str]:
        """Try to infer state from organization name or text"""
        if not text:
            return None

        text_lower = text.lower()

        # Look for explicit state mentions
        for code, name in BRAZILIAN_STATES.items():
            if name.lower() in text_lower or f"estado de {name.lower()}" in text_lower:
                return code

        # Look for common patterns
        state_patterns = {
            'são paulo': 'SP', 'rio de janeiro': 'RJ', 'minas gerais': 'MG',
            'rio grande do sul': 'RS', 'paraná': 'PR', 'santa catarina': 'SC',
            'bahia': 'BA', 'goiás': 'GO', 'pernambuco': 'PE', 'ceará': 'CE'
        }

        for pattern, code in state_patterns.items():
            if pattern in text_lower:
                return code

        return None

    def classify_tender(self, tender_data: Dict) -> ClassificationResult:
        """Complete tender classification with enhanced location and API data extraction"""

        # Extract basic data
        cnpj = tender_data.get('cnpj', '')
        org_name = tender_data.get('organization_name', '') or tender_data.get('razaoSocial', '')
        tender_title = tender_data.get('title', '') or tender_data.get('objeto', '')
        tender_description = tender_data.get('description', '') or tender_data.get('informacaoComplementar', '')
        items_description = tender_data.get('items_summary', '')

        # Extract values - prioritize homologated over estimated
        total_value = (
            tender_data.get('total_homologated_value') or
            tender_data.get('valorTotalHomologado') or
            tender_data.get('total_estimated_value') or
            tender_data.get('valorTotalEstimado') or 0
        )

        # Extract location information
        state_code, state_name, city = self.extract_location_info(tender_data)

        # Extract structured API data
        modality_id = tender_data.get('modalidadeId')
        modality_name = tender_data.get('modalidadeNome')

        # Check if this involves materials (vs services)
        is_material = None
        items = tender_data.get('itens', []) or tender_data.get('itensCompra', [])
        if items:
            # Check if any items are materials
            material_items = [item for item in items if item.get('materialOuServico') == 'M']
            is_material = len(material_items) > 0

        # Classify government level
        gov_level, gov_confidence, gov_reasoning = self.classify_government_level(
            cnpj, org_name, tender_title, tender_description, tender_data)

        # Classify organization type
        org_type, org_confidence, org_reasoning = self.classify_organization_type(
            org_name, tender_title, tender_description, tender_data)

        # Classify tender size
        tender_size = classify_tender_size(total_value)

        # Assess medical relevance
        is_medical, medical_score, medical_keywords, medical_reasoning = self.assess_medical_relevance(
            tender_title, tender_description, items_description)

        # Enhanced reasoning with location
        reasoning_parts = [f"Gov Level: {gov_reasoning}", f"Org Type: {org_reasoning}", f"Medical: {medical_reasoning}"]
        if state_name:
            reasoning_parts.append(f"Location: {city or 'Unknown city'}, {state_name}")
        if modality_name:
            reasoning_parts.append(f"Modality: {modality_name}")
        combined_reasoning = "; ".join(reasoning_parts)

        return ClassificationResult(
            # Location
            state_code=state_code,
            state_name=state_name,
            city=city,
            # Government classification
            government_level=gov_level,
            government_level_confidence=gov_confidence,
            # Organization classification
            organization_type=org_type,
            organization_type_confidence=org_confidence,
            # Structured API data
            contracting_modality_id=modality_id,
            contracting_modality_name=modality_name,
            is_material=is_material,
            # Size and relevance
            tender_size=tender_size,
            is_medical_relevant=is_medical,
            medical_relevance_score=medical_score,
            medical_keywords_found=medical_keywords,
            reasoning=combined_reasoning
        )

    def batch_classify(self, tenders_data: List[Dict]) -> List[ClassificationResult]:
        """Classify multiple tenders efficiently"""
        results = []
        for tender_data in tenders_data:
            try:
                result = self.classify_tender(tender_data)
                results.append(result)
            except Exception as e:
                logger.error(f"Error classifying tender {tender_data.get('control_number', 'unknown')}: {e}")
                # Return unknown classification with new fields
                results.append(ClassificationResult(
                    state_code=None,
                    state_name=None,
                    city=None,
                    government_level=GovernmentLevel.UNKNOWN,
                    government_level_confidence=0,
                    organization_type=OrganizationType.OTHER,
                    organization_type_confidence=0,
                    contracting_modality_id=None,
                    contracting_modality_name=None,
                    is_material=None,
                    tender_size=TenderSize.SMALL,
                    is_medical_relevant=False,
                    medical_relevance_score=0,
                    medical_keywords_found=[],
                    reasoning=f"Classification failed: {str(e)}"
                ))
        return results

    def filter_relevant_tenders(self, tenders_data: List[Dict],
                              min_medical_score: float = 15.0,
                              allowed_gov_levels: List[GovernmentLevel] = None,
                              min_value: float = 1000.0) -> List[Dict]:
        """Filter tenders based on relevance criteria"""

        if allowed_gov_levels is None:
            allowed_gov_levels = [GovernmentLevel.FEDERAL, GovernmentLevel.STATE, GovernmentLevel.MUNICIPAL]

        classifications = self.batch_classify(tenders_data)
        filtered_tenders = []

        for tender_data, classification in zip(tenders_data, classifications):
            # Check medical relevance
            if classification.medical_relevance_score < min_medical_score:
                continue

            # Check government level
            if classification.government_level not in allowed_gov_levels:
                continue

            # Check minimum value
            total_value = tender_data.get('total_homologated_value', 0) or tender_data.get('total_estimated_value', 0)
            if total_value < min_value:
                continue

            # Add classification data to tender
            tender_data['classification'] = classification
            filtered_tenders.append(tender_data)

        logger.info(f"Filtered {len(filtered_tenders)} relevant tenders from {len(tenders_data)} total")
        return filtered_tenders


# Utility functions for analysis
def analyze_classifications(classifications: List[ClassificationResult]) -> Dict[str, any]:
    """Analyze classification results for insights"""

    analysis = {
        'total_tenders': len(classifications),
        'government_level_distribution': {},
        'organization_type_distribution': {},
        'tender_size_distribution': {},
        'medical_relevance_stats': {
            'relevant_count': 0,
            'avg_medical_score': 0,
            'top_medical_keywords': {}
        },
        'location_distribution': {},
        'modality_distribution': {}
    }

    # Count distributions
    for result in classifications:
        # Government level
        gov_level = result.government_level.value
        analysis['government_level_distribution'][gov_level] = \
            analysis['government_level_distribution'].get(gov_level, 0) + 1

        # Organization type
        org_type = result.organization_type.value
        analysis['organization_type_distribution'][org_type] = \
            analysis['organization_type_distribution'].get(org_type, 0) + 1

        # Tender size
        size = result.tender_size.value
        analysis['tender_size_distribution'][size] = \
            analysis['tender_size_distribution'].get(size, 0) + 1

        # Medical relevance
        if result.is_medical_relevant:
            analysis['medical_relevance_stats']['relevant_count'] += 1

        # Medical keywords
        for keyword in result.medical_keywords_found:
            analysis['medical_relevance_stats']['top_medical_keywords'][keyword] = \
                analysis['medical_relevance_stats']['top_medical_keywords'].get(keyword, 0) + 1

        # Location distribution
        if result.state_name:
            analysis['location_distribution'][result.state_name] = \
                analysis['location_distribution'].get(result.state_name, 0) + 1

        # Modality distribution
        if result.contracting_modality_name:
            analysis['modality_distribution'][result.contracting_modality_name] = \
                analysis['modality_distribution'].get(result.contracting_modality_name, 0) + 1

    # Calculate averages
    if classifications:
        analysis['medical_relevance_stats']['avg_medical_score'] = \
            sum(r.medical_relevance_score for r in classifications) / len(classifications)

    return analysis


# Test function
def test_classifier():
    """Test the classifier with sample data"""

    sample_tenders = [
        {
            'cnpj': '26.989.715/0001-23',
            'organization_name': 'MINISTÉRIO DA SAÚDE',
            'razaoSocial': 'MINISTÉRIO DA SAÚDE',
            'title': 'PREGÃO ELETRÔNICO - AQUISIÇÃO DE CURATIVOS TRANSPARENTES',
            'objeto': 'PREGÃO ELETRÔNICO - AQUISIÇÃO DE CURATIVOS TRANSPARENTES',
            'description': 'Aquisição de materiais médicos hospitalares: curativos transparentes fenestrados com borda adesiva',
            'valorTotalHomologado': 150000.00,
            'modalidadeId': 6,
            'modalidadeNome': 'Pregão - Eletrônico',
            'uf': 'DF',
            'municipio': 'Brasília',
            'esferaFederal': True,
            'itens': [{'materialOuServico': 'M'}]
        },
        {
            'cnpj': '87.316.755/0001-86',
            'organization_name': 'PREFEITURA MUNICIPAL DE SÃO PAULO',
            'razaoSocial': 'PREFEITURA MUNICIPAL DE SÃO PAULO',
            'title': 'COMPRA DE EQUIPAMENTOS DE INFORMÁTICA',
            'objeto': 'COMPRA DE EQUIPAMENTOS DE INFORMÁTICA',
            'description': 'Aquisição de computadores e equipamentos de TI para secretarias municipais',
            'valorTotalHomologado': 75000.00,
            'modalidadeId': 6,
            'modalidadeNome': 'Pregão - Eletrônico',
            'uf': 'SP',
            'municipio': 'São Paulo',
            'esferaMunicipal': True,
            'itens': [{'materialOuServico': 'M'}]
        },
        {
            'cnpj': '46.374.500/0001-19',
            'organization_name': 'HOSPITAL DAS CLÍNICAS DA UNIVERSIDADE DE SÃO PAULO',
            'razaoSocial': 'HOSPITAL DAS CLÍNICAS DA UNIVERSIDADE DE SÃO PAULO',
            'title': 'MATERIAIS MÉDICO-HOSPITALARES',
            'objeto': 'MATERIAIS MÉDICO-HOSPITALARES',
            'description': 'Curativos, gazes, seringas, materiais para centro cirúrgico',
            'valorTotalHomologado': 500000.00,
            'modalidadeId': 4,
            'modalidadeNome': 'Concorrência - Eletrônica',
            'uf': 'SP',
            'municipio': 'São Paulo',
            'esferaEstadual': True,
            'itens': [{'materialOuServico': 'M'}, {'materialOuServico': 'M'}]
        }
    ]

    classifier = TenderClassifier()
    results = classifier.batch_classify(sample_tenders)

    print("=== TENDER CLASSIFICATION RESULTS ===")
    for tender, result in zip(sample_tenders, results):
        print(f"\nOrganization: {tender['organization_name']}")
        print(f"Title: {tender['title']}")
        print(f"Location: {result.city or 'Unknown'}, {result.state_name or 'Unknown State'} ({result.state_code or 'N/A'})")
        print(f"Government Level: {result.government_level.value} (confidence: {result.government_level_confidence:.1f}%)")
        print(f"Organization Type: {result.organization_type.value} (confidence: {result.organization_type_confidence:.1f}%)")
        print(f"Contracting Modality: {result.contracting_modality_name or 'Unknown'} (ID: {result.contracting_modality_id or 'N/A'})")
        print(f"Is Material: {result.is_material}")
        print(f"Tender Size: {result.tender_size.value}")
        print(f"Medical Relevant: {result.is_medical_relevant} (score: {result.medical_relevance_score:.1f})")
        print(f"Medical Keywords: {result.medical_keywords_found[:5]}")
        print(f"Reasoning: {result.reasoning}")
        print("-" * 50)

    # Test filtering
    filtered = classifier.filter_relevant_tenders(sample_tenders)
    print(f"\nFiltered {len(filtered)} relevant tenders from {len(sample_tenders)} total")

if __name__ == "__main__":
    test_classifier()