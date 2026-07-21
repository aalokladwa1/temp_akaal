"""
AKAAL Platform 5 — CompatibilityAnalyzer Subsystem

Orchestrates SchemaComparator, RiskClassifier, and CompatibilityReportBuilder.
"""

from akaal.schema.compatibility.comparator import SchemaComparator, SchemaDiff
from akaal.schema.compatibility.report import CompatibilityReport, CompatibilityReportBuilder
from akaal.schema.compatibility.risk import RiskClassifier
from akaal.schema.versioning.snapshot import SchemaSnapshot


class CompatibilityAnalyzer:
    """Analyzer executing end-to-end schema compatibility analysis between two snapshots."""

    def __init__(self) -> None:
        self.comparator = SchemaComparator()
        self.risk_classifier = RiskClassifier()

    def analyze(self, source_snapshot: SchemaSnapshot, target_snapshot: SchemaSnapshot) -> CompatibilityReport:
        diff = self.comparator.compare(source_snapshot, target_snapshot)
        evaluation = self.risk_classifier.classify(diff)
        return CompatibilityReportBuilder.build_report(evaluation)
