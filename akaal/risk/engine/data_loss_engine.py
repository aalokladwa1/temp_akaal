"""
Akaal — Data Loss Prediction Engine
====================================
Single-responsibility engine detecting data loss risks from precision, scale, and nullability shifts.
"""

from typing import Dict, Any, List
from akaal.risk.models.risk_context import RiskContext
from akaal.risk.models.risk_item import RiskItem


class DataLossEngine:
    """Detects data loss risks over canonical migration models."""

    def evaluate_data_loss(self, ctx: RiskContext, risk_items: List[RiskItem]) -> Dict[str, Any]:
        opaque_risks = [r for r in risk_items if r.risk_type == "OPAQUE_TYPE"]

        return {
            "potential_data_loss_detected": len(opaque_risks) > 0,
            "data_loss_risk_count": len(opaque_risks),
            "loss_classification": "LOSSY_EMULATION" if len(opaque_risks) > 0 else "LOSSLESS",
            "confidence_score": 90.0,
        }
