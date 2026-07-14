"""
Akaal — Type Conversion Diagnostics
===================================
Contains diagnostic models, recommendation formats, and severity levels.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Tuple

class DiagnosticSeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class DiagnosticCategory(str, Enum):
    PRECISION = "PRECISION"
    SCALE = "SCALE"
    TIMEZONE = "TIMEZONE"
    COMPATIBILITY = "COMPATIBILITY"
    POLICY = "POLICY"
    ENGINE = "ENGINE"


class RecommendationCategory(str, Enum):
    DATALOSS = "DATALOSS"
    PERFORMANCE = "PERFORMANCE"
    COMPATIBILITY = "COMPATIBILITY"
    MANUAL_ACTION = "MANUAL_ACTION"


@dataclass(frozen=True)
class StructuredRecommendation:
    category: RecommendationCategory
    severity: DiagnosticSeverity
    description: str
    auto_applicable: bool = False
    migration_actions: Tuple[str, ...] = field(default_factory=tuple)
    doc_references: Tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class Diagnostic:
    code: str
    severity: DiagnosticSeverity
    category: DiagnosticCategory
    message: str
    related_object: Optional[str] = None
    remediation: Optional[StructuredRecommendation] = None
