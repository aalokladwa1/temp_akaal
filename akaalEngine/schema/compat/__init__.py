"""
akaalEngine.schema.compat
=========================
Compatibility Pack foundation (akaal_compat), Canonical Schema Comparator,
Incremental DDL Engine, and Risk Scorer.
"""

from akaalEngine.schema.compat.comparator import (
    CanonicalDriftAnalyzer,
    CanonicalSchemaComparator,
    CompatibilityClassification,
    DifferenceCategory,
    DriftClassification,
    IncrementalDDLAction,
    RiskSeverity,
    SchemaDifference,
    SchemaDiffEngine,
    SchemaDriftReport,
)
from akaalEngine.schema.compat.lifecycle import (
    CompatibilityPackReport,
    CompatibilityRequirement,
    CompatibilityRequirementTracker,
)
from akaalEngine.schema.compat.pack_definitions import (
    CompatibilityFunctionDef,
    CompatibilityPackDefinitions,
)
from akaalEngine.schema.compat.risk_scorer import (
    CanonicalRiskScorer,
    RiskAssessment,
    RiskFinding,
)

__all__ = [
    "CanonicalSchemaComparator",
    "SchemaDiffEngine",
    "IncrementalDDLAction",
    "SchemaDifference",
    "DifferenceCategory",
    "CompatibilityClassification",
    "RiskSeverity",
    "CanonicalRiskScorer",
    "RiskAssessment",
    "RiskFinding",
    "CanonicalDriftAnalyzer",
    "SchemaDriftReport",
    "DriftClassification",
    "CompatibilityFunctionDef",
    "CompatibilityPackDefinitions",
    "CompatibilityRequirement",
    "CompatibilityPackReport",
    "CompatibilityRequirementTracker",
]
