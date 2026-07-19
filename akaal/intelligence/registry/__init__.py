"""
AKAAL Enterprise Intelligence Registry Subsystem Package
=========================================================
Re-exports EnterpriseIntelligenceRegistry and custom registry exceptions.
"""

from akaal.intelligence.registry.enterprise_intelligence_registry import (
    EnterpriseIntelligenceRegistry,
    EnterpriseIntelligenceRegistryError,
)

__all__ = [
    "EnterpriseIntelligenceRegistry",
    "EnterpriseIntelligenceRegistryError",
]
