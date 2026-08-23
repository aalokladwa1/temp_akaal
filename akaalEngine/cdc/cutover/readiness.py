"""
akaalEngine.cdc.cutover.readiness
=================================
TechnicalCutoverReadinessGate evaluating fact-based cutover readiness.
"""

from typing import Any, Dict

from akaalEngine.cdc.models.cutover import TechnicalCutoverReadinessFacts


class TechnicalCutoverReadinessGate:
    """Evaluates whether all technical readiness facts permit cutover execution."""

    @classmethod
    def evaluate_readiness(cls, facts: TechnicalCutoverReadinessFacts) -> bool:
        return facts.is_technical_cutover_ready
