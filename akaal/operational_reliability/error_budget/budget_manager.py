"""
AKAAL Platform 7 — Error Budget & Burn Rate Manager.
"""

from typing import Dict
from akaal.operational_reliability.domain.models import ErrorBudget


class ErrorBudgetManager:
    """Calculates error budget consumption, burn rate, and budget exhaustion thresholds."""

    def compute_budget(self, slo_id: str, target_pct: float, current_pct: float, total_minutes_in_window: float = 43200.0) -> ErrorBudget:
        total_budget_minutes = total_minutes_in_window * ((100.0 - target_pct) / 100.0)
        unavailability_pct = max(0.0, 100.0 - current_pct)
        consumed_minutes = total_minutes_in_window * (unavailability_pct / 100.0)
        remaining_minutes = max(0.0, total_budget_minutes - consumed_minutes)
        consumed_pct = round((consumed_minutes / max(0.001, total_budget_minutes)) * 100.0, 2)

        burn_rate_1h = round(consumed_pct / 10.0, 2)
        burn_rate_24h = round(consumed_pct / 100.0, 2)

        return ErrorBudget(
            slo_id=slo_id,
            total_budget_minutes=round(total_budget_minutes, 2),
            remaining_budget_minutes=round(remaining_minutes, 2),
            consumed_percentage=min(100.0, consumed_pct),
            burn_rate_1h=burn_rate_1h,
            burn_rate_24h=burn_rate_24h,
            is_exhausted=remaining_minutes <= 0.0,
        )
