from dataclasses import dataclass

@dataclass(frozen=True)
class ReliabilityDiagnostic:
    message: str
    severity: str  # ERROR, WARNING, INFO
    category: str  # VALIDATION, HEALTH, COMPLIANCE
    recommendation: str
