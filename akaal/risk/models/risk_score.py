"""
Akaal — Risk Score Dataclass
============================
Overall risk score and dimensional scores.
"""

from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class RiskScore:
    overall_risk_score: float = 0.0  # 0.0 (no risk) to 100.0 (extreme risk)
    compatibility_risk_score: float = 0.0
    performance_risk_score: float = 0.0
    data_loss_risk_score: float = 0.0
    downtime_risk_score: float = 0.0
    complexity_risk_score: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall_risk_score": round(self.overall_risk_score, 2),
            "compatibility_risk_score": round(self.compatibility_risk_score, 2),
            "performance_risk_score": round(self.performance_risk_score, 2),
            "data_loss_risk_score": round(self.data_loss_risk_score, 2),
            "downtime_risk_score": round(self.downtime_risk_score, 2),
            "complexity_risk_score": round(self.complexity_risk_score, 2),
        }
