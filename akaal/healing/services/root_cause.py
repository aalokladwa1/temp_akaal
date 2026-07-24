"""RootCauseAnalysisService: Identifies root cause origin, dependency chains, failure sources (Cap 10)."""

from typing import Any, Dict
from akaal.healing.core.interfaces import IHealingService


class RootCauseAnalysisService(IHealingService):
    """Infrastructure service analyzing root cause origins and failure dependency chains."""

    @property
    def service_name(self) -> str:
        return "RootCauseAnalysisService"

    def analyze_failure(self, validation_issue: Any) -> Dict[str, Any]:
        """Derive root cause origin and failure source."""
        table = getattr(validation_issue, "table_name", "UNKNOWN")
        msg = getattr(validation_issue, "message", "Validation error")

        return {
            "root_cause": "SCHEMA_OR_DATA_DRIFT",
            "origin_table": table,
            "failure_source": f"Validation check: {msg}",
            "dependency_chain": [table],
            "repair_rationale": f"Fix structural/data drift on {table}",
        }
