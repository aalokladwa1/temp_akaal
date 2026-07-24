"""
AKAAL Platform 7 — Service Classification Engine.
"""

from typing import List
from akaal.operational_reliability.domain.models import ServiceDescriptor
from akaal.operational_reliability.domain.enums import ServiceTier, CriticalityLevel


class ServiceClassificationEngine:
    """Classifies operational service criticality and deployment risk tiers."""

    def filter_critical_services(self, services: List[ServiceDescriptor]) -> List[ServiceDescriptor]:
        return [s for s in services if s.tier == ServiceTier.TIER_0 or s.criticality == CriticalityLevel.CRITICAL]
