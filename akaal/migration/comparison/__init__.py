"""
Akaal — Migration Comparison Package
====================================
Consolidates all planning-level identity diff and compatibility classification engines.
"""

from akaal.migration.comparison.identity import (
    IdentityComparisonEngine,
    CompatibilityCategory,
    ApprovalRequirement,
    IdentityDiagnostic,
    IdentityComparisonReport,
)

__all__ = [
    "IdentityComparisonEngine",
    "CompatibilityCategory",
    "ApprovalRequirement",
    "IdentityDiagnostic",
    "IdentityComparisonReport",
]
