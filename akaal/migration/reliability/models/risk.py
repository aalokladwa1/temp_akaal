from enum import Enum
from dataclasses import dataclass
from typing import Tuple

class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

@dataclass(frozen=True)
class RiskAssessment:
    confidence_score: float
    risk_score: float
    risk_level: RiskLevel
    explanation: str
    recommendations: Tuple[str, ...]
