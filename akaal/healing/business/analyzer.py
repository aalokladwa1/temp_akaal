"""BusinessImpactAnalyzer: Revenue, compliance, customer, and SLA impact analysis."""

from dataclasses import dataclass
from typing import List, Dict, Any
from akaal.healing.business.criticality import CriticalityEvaluator, RiskLevel


@dataclass
class BusinessImpactReport:
    table_name: str
    risk_level: RiskLevel
    revenue_impact_score: float
    compliance_impact_score: float
    requires_executive_approval: bool


class BusinessImpactAnalyzer:
    """Analyzes business revenue, compliance, and SLA impact for proposed repairs."""

    def __init__(self):
        self.criticality_evaluator = CriticalityEvaluator()

    def analyze(self, table_name: str) -> BusinessImpactReport:
        """Generate business impact report for table."""
        risk = self.criticality_evaluator.evaluate_table(table_name)
        exec_approval = risk == RiskLevel.CRITICAL

        return BusinessImpactReport(
            table_name=table_name,
            risk_level=risk,
            revenue_impact_score=90.0 if risk == RiskLevel.CRITICAL else 20.0,
            compliance_impact_score=95.0 if risk == RiskLevel.CRITICAL else 30.0,
            requires_executive_approval=exec_approval,
        )
