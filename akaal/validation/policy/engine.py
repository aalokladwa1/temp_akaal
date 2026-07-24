"""PolicyEngine: Enterprise validation policy profiles and compliance rule engine."""

from typing import Dict, Any, List
from akaal.validation.core.interfaces import IPolicy
from akaal.validation.core.config import PolicyProfile
from akaal.validation.core.models import ValidationResult, ValidationStatus, SeverityLevel


class PolicyEngine(IPolicy):
    """Evaluates validation results against enterprise policy compliance rules."""

    def __init__(self, profile: PolicyProfile = PolicyProfile.DEV):
        self.profile = profile

    @property
    def policy_name(self) -> str:
        return f"EnterprisePolicyEngine({self.profile.value})"

    def evaluate(self, result: ValidationResult) -> Dict[str, Any]:
        """Evaluate policy compliance against result based on selected profile."""
        compliant = True
        violations = []

        if self.profile == PolicyProfile.FINANCE:
            # 100% zero tolerance policy
            if result.failed_count > 0:
                compliant = False
                violations.append("Finance Policy: Zero tolerance for data discrepancies.")
            if result.confidence_score < 99.9:
                compliant = False
                violations.append("Finance Policy: Confidence score below 99.9% threshold.")

        elif self.profile == PolicyProfile.HEALTHCARE:
            # HIPAA & LOB validation policy
            critical_issues = [i for i in result.issues if i.severity == SeverityLevel.CRITICAL]
            if critical_issues:
                compliant = False
                violations.append(f"Healthcare Policy: Discovered {len(critical_issues)} critical HIPAA compliance issues.")

        elif self.profile == PolicyProfile.GOVERNMENT:
            if result.confidence_score < 98.0:
                compliant = False
                violations.append("Government Policy: Confidence score below 98.0%.")

        elif self.profile in (PolicyProfile.DEV, PolicyProfile.TEST):
            if any(i.severity == SeverityLevel.CRITICAL for i in result.issues):
                compliant = False
                violations.append("Dev/Test Policy: Critical error present.")

        return {
            "policy_profile": self.profile.value,
            "compliant": compliant,
            "violations": violations,
            "confidence_score": result.confidence_score,
        }
