from __future__ import annotations
from typing import Dict, Any

class RiskScorerV1:
    """
    V1 Risk Scorer (Deterministic Safety Annotation Layer)

    RULES:
    - NO heuristics
    - NO ML
    - NO inference
    - ONLY deterministic rule tables
    - MUST NOT modify UDM
    - ONLY annotate risk
    """

    # -----------------------------
    # FIXED FAMILY RISK TABLE (DETERMINISTIC)
    # -----------------------------
    FAMILY_RISK_TABLE = {
        "numeric": 1,
        "boolean": 1,
        "string": 2,
        "identifier": 2,
        "temporal": 3,
        "structured": 4,
        "binary": 4,
        "network": 4,
        "spatial": 5,
    }

    def score(self, udm: Dict[str, Any]) -> Dict[str, Any]:
        # -----------------------------
        # INVARIANT VALIDATION
        # -----------------------------
        if not udm or "concept" not in udm or "family" not in udm:
            raise ValueError("Invalid UDM input: Missing 'concept' or 'family' keys.")

        family = udm["family"]

        if family not in self.FAMILY_RISK_TABLE:
            raise ValueError(f"Unsupported family: {family}")

        risk_score = self.FAMILY_RISK_TABLE[family]
        risk_flags = []

        # -----------------------------
        # PRECISION RULES
        # -----------------------------
        precision = udm.get("precision")
        if precision is not None:
            if precision > 18:
                risk_score += 2
                risk_flags.append("HIGH_PRECISION_OVERFLOW_RISK")

        # -----------------------------
        # SCALE RULES
        # -----------------------------
        scale = udm.get("scale")
        if scale is not None:
            if scale > 6:
                risk_score += 2
                risk_flags.append("HIGH_SCALE_PRECISION_LOSS_RISK")

        # -----------------------------
        # LENGTH RULES
        # -----------------------------
        length = udm.get("length")
        if length is not None:
            if length > 1024:
                risk_score += 2
                risk_flags.append("LARGE_FIELD_TRUNCATION_RISK")

        # -----------------------------
        # TIMEZONE RULES
        # -----------------------------
        if udm.get("timezone") is True:
            risk_score += 1
            risk_flags.append("TIMEZONE_NORMALIZATION_REQUIRED")

        # -----------------------------
        # SPATIAL / NETWORK SAFETY SIGNAL
        # -----------------------------
        if family in ("spatial", "network"):
            risk_flags.append("spatial_network_mismatch")
            risk_score += 2

        # -----------------------------
        # FINAL CLASSIFICATION (STRICT BINS)
        # -----------------------------
        if risk_score <= 2:
            level = "LOW"
        elif risk_score <= 4:
            level = "MEDIUM"
        elif risk_score <= 6:
            level = "HIGH"
        else:
            level = "CRITICAL"

        return {
            "udm": udm,
            "risk": {
                "score": risk_score,
                "level": level,
                "flags": risk_flags,
            },
        }

def score_risk(udm: Dict[str, Any]) -> Dict[str, Any]:
    return RiskScorerV1().score(udm)