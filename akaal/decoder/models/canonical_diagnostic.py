"""
Akaal — Canonical Diagnostic Model
==================================
Structured diagnostic model for Decoder normalization errors, validation warnings, and telemetry.
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
class CanonicalDiagnostic:
    diagnostic_id: str
    severity: DiagnosticSeverity
    category: str
    affected_objects: List[str] = field(default_factory=list)
    root_cause: str = ""
    recommended_resolution: str = ""
    documentation_link: str = "https://docs.akaal.io/decoder/diagnostics"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "diagnostic_id": self.diagnostic_id,
            "severity": self.severity.value if hasattr(self.severity, "value") else str(self.severity),
            "category": self.category,
            "affected_objects": self.affected_objects,
            "root_cause": self.root_cause,
            "recommended_resolution": self.recommended_resolution,
            "documentation_link": self.documentation_link,
        }
