"""
Akaal — Advisor Registry Package
================================
Re-exports AdvisorRegistry and AdvisorRegistryError.
"""

from akaal.advisor.registry.advisor_registry import (
    AdvisorRegistry,
    AdvisorRegistryError,
)

__all__ = ["AdvisorRegistry", "AdvisorRegistryError"]
