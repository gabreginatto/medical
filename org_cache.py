"""
Organization Caching System for Medical Tender Discovery
Caches known medical organizations to speed up discovery and filtering
"""

import json
import logging
import time
from typing import Dict, List, Optional, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from pathlib import Path

from config import OrganizationType, GovernmentLevel

logger = logging.getLogger(__name__)

@dataclass
class CachedOrganization:
    """Cached organization information"""
    cnpj: str
    name: str
    organization_type: str  # OrganizationType value
    government_level: str  # GovernmentLevel value
    state_code: str
    is_medical: bool
    medical_confidence: float
    last_updated: str  # ISO format datetime
    tender_count: int = 0  # Number of tenders processed from this org

class OrganizationCache:
    """
    Multi-level caching system for organizations, tenders, and items
    Reduces need for full classification on every tender discovery
    """

    def __init__(self, cache_file: str = "org_cache.json"):
        self.cache_file = Path(cache_file)
        self.medical_orgs: Dict[str, CachedOrganization] = {}
        self.non_medical_orgs: Set[str] = set()
        self.cache_max_age_days = 30  # Refresh cache after 30 days

        # Multi-level caching (new)
        self.tender_cache: Dict[str, Dict] = {}  # tender_key -> tender_data
        self.item_cache: Dict[str, List[Dict]] = {}  # tender_key -> items_list
        self.tender_cache_ttl = 3600  # 1 hour TTL for tender cache
        self.item_cache_ttl = 3600  # 1 hour TTL for item cache

        # Load cache if exists
        self.load_cache()

        # Known major medical organizations (seed data)
        self.known_medical_cnpjs = {
            # Major federal hospitals and health agencies
            '26989715': 'Ministério da Saúde',
            '00394544': 'ANVISA',
            '33781055': 'Fiocruz',

            # São Paulo major hospitals
            '46374500': 'Hospital das Clínicas - USP',
            '46392130': 'UNIFESP - Hospital São Paulo',
            '60742616': 'Hospital Albert Einstein',
            '61599908': 'Hospital Sírio-Libanês',

            # Rio de Janeiro major hospitals
            '42498717': 'Hospital Universitário Clementino Fraga Filho - UFRJ',
            '28481581': 'INCA - Instituto Nacional do Câncer',

            # Add more as discovered
        }

    def is_cached_medical_org(self, cnpj: str) -> Optional[tuple]:
        """
        Quick check if organization is cached as medical
        Returns (is_medical, confidence) or None if not cached
        """
        # Normalize CNPJ
        cnpj_clean = self._normalize_cnpj(cnpj)

        # Check if in medical cache
        if cnpj_clean in self.medical_orgs:
            cached = self.medical_orgs[cnpj_clean]

            # Check if cache is fresh
            last_updated = datetime.fromisoformat(cached.last_updated)
            age_days = (datetime.now() - last_updated).days

            if age_days <= self.cache_max_age_days:
                return (True, cached.medical_confidence)
            else:
                # Cache expired, remove it
                del self.medical_orgs[cnpj_clean]
                return None

        # Check if in non-medical cache
        if cnpj_clean in self.non_medical_orgs:
            return (False, 90.0)  # High confidence it's not medical

        # Check known medical CNPJs (seed data)
        cnpj_prefix = cnpj_clean[:8]  # First 8 digits
        if cnpj_prefix in self.known_medical_cnpjs:
            return (True, 95.0)  # High confidence from seed data

        return None  # Not in cache

    def add_medical_organization(self, cnpj: str, name: str,
                                org_type: OrganizationType,
                                gov_level: GovernmentLevel,
                                state_code: str,
                                medical_confidence: float):
        """Add organization to medical cache"""
        cnpj_clean = self._normalize_cnpj(cnpj)

        cached_org = CachedOrganization(
            cnpj=cnpj_clean,
            name=name,
            organization_type=org_type.value,
            government_level=gov_level.value,
            state_code=state_code,
            is_medical=True,
            medical_confidence=medical_confidence,
            last_updated=datetime.now().isoformat(),
            tender_count=1
        )

        self.medical_orgs[cnpj_clean] = cached_org
        logger.info(f"Cached medical org: {name} ({cnpj_clean})")

    def add_non_medical_organization(self, cnpj: str):
        """Add organization to non-medical cache"""
        cnpj_clean = self._normalize_cnpj(cnpj)
        self.non_medical_orgs.add(cnpj_clean)

    def increment_tender_count(self, cnpj: str):
        """Increment tender count for cached organization"""
        cnpj_clean = self._normalize_cnpj(cnpj)
        if cnpj_clean in self.medical_orgs:
            self.medical_orgs[cnpj_clean].tender_count += 1

    def get_medical_orgs_by_state(self, state_code: str) -> List[str]:
        """Get list of cached medical organization CNPJs for a specific state"""
        return [
            org.cnpj for org in self.medical_orgs.values()
            if org.state_code == state_code
        ]

    def get_top_medical_orgs(self, state_code: Optional[str] = None,
                            limit: int = 50) -> List[CachedOrganization]:
        """Get top medical organizations by tender count"""
        orgs = list(self.medical_orgs.values())

        if state_code:
            orgs = [org for org in orgs if org.state_code == state_code]

        # Sort by tender count (descending)
        orgs.sort(key=lambda x: x.tender_count, reverse=True)

        return orgs[:limit]

    def _normalize_cnpj(self, cnpj: str) -> str:
        """Normalize CNPJ to digits only"""
        if not cnpj:
            return ""
        return ''.join(filter(str.isdigit, cnpj))

    def save_cache(self):
        """Save cache to disk"""
        cache_data = {
            'medical_orgs': {
                cnpj: asdict(org) for cnpj, org in self.medical_orgs.items()
            },
            'non_medical_orgs': list(self.non_medical_orgs),
            'last_saved': datetime.now().isoformat()
        }

        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved organization cache: {len(self.medical_orgs)} medical orgs")
        except Exception as e:
            logger.error(f"Error saving cache: {e}")

    def load_cache(self):
        """Load cache from disk"""
        if not self.cache_file.exists():
            logger.info("No existing cache file found")
            return

        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)

            # Load medical orgs
            medical_orgs_data = cache_data.get('medical_orgs', {})
            for cnpj, org_dict in medical_orgs_data.items():
                self.medical_orgs[cnpj] = CachedOrganization(**org_dict)

            # Load non-medical orgs
            self.non_medical_orgs = set(cache_data.get('non_medical_orgs', []))

            logger.info(f"Loaded cache: {len(self.medical_orgs)} medical orgs, "
                       f"{len(self.non_medical_orgs)} non-medical orgs")

        except Exception as e:
            logger.error(f"Error loading cache: {e}")
            self.medical_orgs = {}
            self.non_medical_orgs = set()

    def get_statistics(self) -> Dict:
        """Get cache statistics"""
        return {
            'total_medical_orgs': len(self.medical_orgs),
            'total_non_medical_orgs': len(self.non_medical_orgs),
            'medical_orgs_by_state': self._count_by_state(),
            'medical_orgs_by_type': self._count_by_type(),
            'top_orgs_by_tenders': [
                {'name': org.name, 'cnpj': org.cnpj, 'tender_count': org.tender_count}
                for org in self.get_top_medical_orgs(limit=10)
            ]
        }

    def _count_by_state(self) -> Dict[str, int]:
        """Count medical orgs by state"""
        counts = {}
        for org in self.medical_orgs.values():
            counts[org.state_code] = counts.get(org.state_code, 0) + 1
        return counts

    def _count_by_type(self) -> Dict[str, int]:
        """Count medical orgs by type"""
        counts = {}
        for org in self.medical_orgs.values():
            counts[org.organization_type] = counts.get(org.organization_type, 0) + 1
        return counts

    def clear_expired_entries(self):
        """Remove entries older than cache_max_age_days"""
        cutoff_date = datetime.now() - timedelta(days=self.cache_max_age_days)
        expired_cnpjs = []

        for cnpj, org in self.medical_orgs.items():
            last_updated = datetime.fromisoformat(org.last_updated)
            if last_updated < cutoff_date:
                expired_cnpjs.append(cnpj)

        for cnpj in expired_cnpjs:
            del self.medical_orgs[cnpj]

        if expired_cnpjs:
            logger.info(f"Removed {len(expired_cnpjs)} expired cache entries")

    # Multi-level caching methods (new)
    def _make_tender_key(self, cnpj: str, year: int, sequential: int) -> str:
        """Generate cache key for tender"""
        return f"{cnpj}_{year}_{sequential}"

    def cache_tender(self, tender_data: Dict):
        """Cache tender data with timestamp"""
        cnpj = tender_data.get('cnpj', '')
        year = tender_data.get('ano') or tender_data.get('anoCompra')
        sequential = tender_data.get('sequencial') or tender_data.get('sequencialCompra')

        if all([cnpj, year, sequential]):
            key = self._make_tender_key(cnpj, year, sequential)
            self.tender_cache[key] = {
                'data': tender_data,
                'timestamp': time.time()
            }

    def get_cached_tender(self, cnpj: str, year: int, sequential: int) -> Optional[Dict]:
        """Get cached tender if not expired"""
        key = self._make_tender_key(cnpj, year, sequential)

        if key in self.tender_cache:
            entry = self.tender_cache[key]
            if time.time() - entry['timestamp'] < self.tender_cache_ttl:
                return entry['data']
            else:
                # Expired, remove it
                del self.tender_cache[key]

        return None

    def cache_items(self, cnpj: str, year: int, sequential: int, items: List[Dict]):
        """Cache tender items with timestamp"""
        key = self._make_tender_key(cnpj, year, sequential)
        self.item_cache[key] = {
            'items': items,
            'timestamp': time.time()
        }

    def get_cached_items(self, cnpj: str, year: int, sequential: int) -> Optional[List[Dict]]:
        """Get cached items if not expired"""
        key = self._make_tender_key(cnpj, year, sequential)

        if key in self.item_cache:
            entry = self.item_cache[key]
            if time.time() - entry['timestamp'] < self.item_cache_ttl:
                return entry['items']
            else:
                # Expired, remove it
                del self.item_cache[key]

        return None

    def clear_tender_caches(self):
        """Clear tender and item caches (for memory management)"""
        cleared_tenders = len(self.tender_cache)
        cleared_items = len(self.item_cache)

        self.tender_cache.clear()
        self.item_cache.clear()

        if cleared_tenders > 0 or cleared_items > 0:
            logger.info(f"Cleared {cleared_tenders} tender caches and {cleared_items} item caches")


# Global cache instance
_cache_instance = None

def get_org_cache(cache_file: str = "org_cache.json") -> OrganizationCache:
    """Get singleton cache instance"""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = OrganizationCache(cache_file)
    return _cache_instance


# Utility functions
def print_cache_statistics(cache: OrganizationCache):
    """Print formatted cache statistics"""
    stats = cache.get_statistics()

    print("=== ORGANIZATION CACHE STATISTICS ===")
    print(f"Total Medical Organizations: {stats['total_medical_orgs']:,}")
    print(f"Total Non-Medical Organizations: {stats['total_non_medical_orgs']:,}")

    print("\n--- Medical Orgs by State ---")
    for state, count in sorted(stats['medical_orgs_by_state'].items()):
        print(f"{state}: {count:,}")

    print("\n--- Medical Orgs by Type ---")
    for org_type, count in sorted(stats['medical_orgs_by_type'].items()):
        print(f"{org_type}: {count:,}")

    print("\n--- Top 10 Orgs by Tender Count ---")
    for i, org in enumerate(stats['top_orgs_by_tenders'], 1):
        print(f"{i}. {org['name']} ({org['cnpj']}): {org['tender_count']} tenders")


# Test function
def test_org_cache():
    """Test organization caching"""
    cache = OrganizationCache("test_cache.json")

    # Add some test organizations
    cache.add_medical_organization(
        "46.374.500/0001-19",
        "Hospital das Clínicas - USP",
        OrganizationType.HOSPITAL,
        GovernmentLevel.STATE,
        "SP",
        95.0
    )

    cache.add_medical_organization(
        "26.989.715/0001-23",
        "Ministério da Saúde",
        OrganizationType.HEALTH_SECRETARIAT,
        GovernmentLevel.FEDERAL,
        "DF",
        98.0
    )

    cache.add_non_medical_organization("12.345.678/0001-99")

    # Test lookups
    print("=== CACHE LOOKUP TESTS ===")
    test_cnpjs = [
        "46.374.500/0001-19",  # Cached medical
        "12.345.678/0001-99",  # Cached non-medical
        "99.999.999/0001-99"   # Not in cache
    ]

    for cnpj in test_cnpjs:
        result = cache.is_cached_medical_org(cnpj)
        if result:
            is_medical, confidence = result
            print(f"{cnpj}: {'Medical' if is_medical else 'Non-medical'} (confidence: {confidence:.1f}%)")
        else:
            print(f"{cnpj}: Not in cache")

    # Save and print stats
    cache.save_cache()
    print("\n")
    print_cache_statistics(cache)

    # Clean up test file
    Path("test_cache.json").unlink(missing_ok=True)


if __name__ == "__main__":
    test_org_cache()
