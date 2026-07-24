"""CriticalityEvaluator & RiskLevel."""

from enum import Enum


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class CriticalityEvaluator:
    """Evaluates business criticality for tables and features."""

    def evaluate_table(self, table_name: str) -> RiskLevel:
        """Evaluate criticality level for target table."""
        name_lower = table_name.lower()
        if "order" in name_lower or "payment" in name_lower or "transaction" in name_lower:
            return RiskLevel.CRITICAL
        elif "user" in name_lower or "account" in name_lower:
            return RiskLevel.HIGH
        else:
            return RiskLevel.MEDIUM
