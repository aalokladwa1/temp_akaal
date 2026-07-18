"""
Akaal — Deterministic Severity Matrix
=====================================
Calculates risk item severity deterministically based on Probability x Impact x Recoverability.
"""

from enum import Enum


class Severity(str, Enum):
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class SeverityMatrix:
    """Deterministic severity calculator."""

    @staticmethod
    def calculate(probability: float, impact: float, recoverability: float) -> Severity:
        """
        probability: 0.0 to 1.0
        impact: 0.0 to 1.0
        recoverability: 0.0 (easy recovery) to 1.0 (irrecoverable loss)
        """
        score = probability * impact * (1.0 + recoverability)

        if score < 0.2:
            return Severity.INFO
        elif score < 0.5:
            return Severity.LOW
        elif score < 0.9:
            return Severity.MEDIUM
        elif score < 1.5:
            return Severity.HIGH
        else:
            return Severity.CRITICAL
