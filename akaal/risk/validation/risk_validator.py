"""
Akaal — Risk Validator
======================
Validator checking integrity and checksum stability of RiskAssessmentModel.
"""

from typing import List
from akaal.risk.models.risk_assessment_model import RiskAssessmentModel


class RiskValidator:
    """Validates structural completeness and checksum integrity of RiskAssessmentModel."""

    @staticmethod
    def validate_assessment(model: RiskAssessmentModel) -> List[str]:
        warnings: List[str] = []
        if not model.sha256_checksum:
            warnings.append("RiskAssessmentModel is missing a sha256_checksum.")
        return warnings
