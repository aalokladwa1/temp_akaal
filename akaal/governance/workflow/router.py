"""
AKAAL Platform 6 — Approval Workflow Router.
"""

from typing import List
from akaal.governance.domain.enums import RiskLevel


class ApprovalWorkflowRouter:
    """Determines required approval roles based on risk level and operation type."""

    def route_workflow_roles(self, risk_level: RiskLevel, target_platform: str) -> List[str]:
        if risk_level == RiskLevel.LOW:
            return ["TeamLead"]
        elif risk_level == RiskLevel.MEDIUM:
            return ["TeamLead", "Manager"]
        elif risk_level == RiskLevel.HIGH:
            return ["TeamLead", "Manager", "ComplianceOfficer"]
        else:  # CRITICAL
            return ["TeamLead", "Manager", "ComplianceOfficer", "ExecutiveApprover"]
