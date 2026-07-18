"""
Akaal — Risk Compatibility Engine
=================================
Single-responsibility engine scoring compatibility over CanonicalMigrationModel objects and semantic mappings.
"""

from typing import Dict, Any, List
from akaal.risk.models.risk_context import RiskContext
from akaal.risk.models.risk_item import RiskItem


class CompatibilityEngine:
    """Evaluates compatibility score over canonical migration models."""

    def evaluate_compatibility(self, ctx: RiskContext, risk_items: List[RiskItem]) -> Dict[str, Any]:
        c_model = ctx.canonical_model
        sem_mappings = c_model.semantic_mappings

        lossless_pct = sem_mappings.get("lossless_percentage", 100.0)
        compat_score = round(lossless_pct, 2)

        return {
            "compatibility_score": compat_score,
            "lossless_count": sem_mappings.get("lossless_count", 0),
            "total_evaluated": sem_mappings.get("total_objects_evaluated", 0),
            "evidence": f"Evaluated compatibility from Decoder semantic mappings ({lossless_pct}% lossless).",
        }
