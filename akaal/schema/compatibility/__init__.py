"""
AKAAL Platform 5 — Schema Compatibility Analysis Subsystem
"""

from akaal.schema.compatibility.comparator import SchemaComparator, SchemaDiff
from akaal.schema.compatibility.risk import RiskClassifier, RiskEvaluation
from akaal.schema.compatibility.report import CompatibilityReport, MigrationAdvisory, CompatibilityReportBuilder
from akaal.schema.compatibility.analyzer import CompatibilityAnalyzer

__all__ = [
    "SchemaComparator",
    "SchemaDiff",
    "RiskClassifier",
    "RiskEvaluation",
    "CompatibilityReport",
    "MigrationAdvisory",
    "CompatibilityReportBuilder",
    "CompatibilityAnalyzer",
]
