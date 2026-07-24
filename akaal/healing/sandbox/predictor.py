"""RiskPredictor: Predicts repair outcome, rollback probability, and repair duration."""

from typing import Any, Dict


class RiskPredictor:
    """Predicts outcome probability and duration for dry-run simulation."""

    def predict(self, plan: Any) -> Dict[str, Any]:
        """Predict simulation metrics."""
        step_count = len(getattr(plan, "steps", []))
        est_duration_ms = step_count * 15.0 + 5.0
        rollback_prob = 0.01 if step_count < 5 else 0.05
        return {
            "estimated_duration_ms": est_duration_ms,
            "rollback_probability": rollback_prob,
            "predicted_success_rate": 1.0 - rollback_prob,
        }
