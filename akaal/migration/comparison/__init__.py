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
from akaal.migration.comparison.partition import (
    PartitionCompatibilityAnalyzer,
    PartitionComparisonEngine,
)

__all__ = [
    "IdentityComparisonEngine",
    "CompatibilityCategory",
    "ApprovalRequirement",
    "IdentityDiagnostic",
    "IdentityComparisonReport",
    "PartitionCompatibilityAnalyzer",
    "PartitionComparisonEngine",
]
