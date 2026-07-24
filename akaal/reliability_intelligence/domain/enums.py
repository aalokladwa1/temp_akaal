"""
AKAAL Platform 9 — Reliability Intelligence Domain Enums.
"""

from enum import Enum


class DriftSeverity(str, Enum):
    NONE = "NONE"
    MINOR = "MINOR"
    MODERATE = "MODERATE"
    SEVERE = "SEVERE"


class RegressionStatus(str, Enum):
    PASSED = "PASSED"
    REGRESSED = "REGRESSED"
    WARNING = "WARNING"
