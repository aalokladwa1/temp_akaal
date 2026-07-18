"""
Akaal — Structured Enterprise Diagnostic Model
==============================================
Structured diagnostic model for conflict engine, validation errors, and health reporting.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List


class DiagnosticSeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class RuleDiagnostic:
    diagnostic_id: str
    severity: DiagnosticSeverity
    category: str
    affected_rules: List[str] = field(default_factory=list)
    root_cause: str = ""
    recommended_resolution: str = ""
    documentation_link: str = "https://docs.akaal.io/rulebook/diagnostics"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "diagnostic_id": self.diagnostic_id,
            "severity": self.severity.value,
            "category": self.category,
            "affected_rules": self.affected_rules,
            "root_cause": self.root_cause,
            "recommended_resolution": self.recommended_resolution,
            "documentation_link": self.documentation_link,
        }
