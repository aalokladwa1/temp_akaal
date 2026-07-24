"""
AKAAL Platform 7 — Service Level Agreement (SLA) Monitoring Service.
"""

from typing import Dict, Any


class SLAMonitoringService:
    """Monitors customer and enterprise SLAs and detects compliance breaches."""

    def evaluate_sla_compliance(self, target_name: str, target_percentage: float, actual_percentage: float) -> Dict[str, Any]:
        is_compliant = actual_percentage >= target_percentage
        return {
            "target_name": target_name,
            "target_percentage": target_percentage,
            "actual_percentage": actual_percentage,
            "is_compliant": is_compliant,
            "margin": round(actual_percentage - target_percentage, 2),
        }
