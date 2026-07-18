"""
Akaal — Risk Diagnostic Model
=============================
Structured diagnostic model for Risk assessment warnings and telemetry.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List
from akaal.decoder.models.canonical_diagnostic import DiagnosticSeverity


@dataclass
class RiskDiagnostic:
    diagnostic_id: str
    severity: DiagnosticSeverity
    category: str
    affected_objects: List[str] = field(default_factory=list)
    root_cause: str = ""
    recommended_resolution: str = ""
    documentation_link: str = "https://docs.akaal.io/risk/diagnostics"

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
