"""
AKAAL Platform 5 — CompatibilityReport & Migration Advisories

Produces structured reports and migration advisories from compatibility evaluation results.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List

from akaal.schema.compatibility.risk import RiskEvaluation
from akaal.schema.domain.enums import RiskLevel


@dataclass
class MigrationAdvisory:
    category: str
    severity: str
    message: str
    recommendation: str


@dataclass
class CompatibilityReport:
    compatibility_score: float
    risk_level: RiskLevel
    breaking_changes: List[str]
    safe_changes: List[str]
    warnings: List[str]
    advisories: List[MigrationAdvisory] = field(default_factory=list)


class CompatibilityReportBuilder:
    """Generates CompatibilityReport and populates migration advisories."""

    @staticmethod
    def build_report(evaluation: RiskEvaluation) -> CompatibilityReport:
        advisories = []

        if evaluation.breaking_changes:
            advisories.append(
                MigrationAdvisory(
                    category="BREAKING_CHANGES",
                    severity="CRITICAL",
                    message=f"Found {len(evaluation.breaking_changes)} breaking schema modifications.",
                    recommendation="Review breaking changes and schedule shadow-column or deprecation phase before deployment.",
                )
            )

        if evaluation.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL):
            advisories.append(
                MigrationAdvisory(
                    category="HIGH_RISK_LOCKS",
                    severity="HIGH",
                    message="High risk of table lock contention during schema modification.",
                    recommendation="Execute migration during off-peak maintenance window or use online DDL algorithms.",
                )
            )

        return CompatibilityReport(
            compatibility_score=evaluation.compatibility_score,
            risk_level=evaluation.risk_level,
            breaking_changes=evaluation.breaking_changes,
            safe_changes=evaluation.safe_changes,
            warnings=evaluation.warnings,
            advisories=advisories,
        )
