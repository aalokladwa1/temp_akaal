"""
akaalEngine.extensions.models.compatibility
===========================================
Models for Semantic Versioning, version ranges, and engine/contract compatibility evaluation results.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class CompatibilityStatus(str, Enum):
    """Evaluation status of version compatibility."""
    COMPATIBLE = "COMPATIBLE"
    INCOMPATIBLE = "INCOMPATIBLE"
    RANGE_MISMATCH = "RANGE_MISMATCH"
    PARSE_ERROR = "PARSE_ERROR"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class CompatibilityRange:
    """Specification of an acceptable SemVer range (e.g. '>=1.0.0, <2.0.0', '^1.2.0', '~1.0')."""
    raw_expression: str

    def __post_init__(self) -> None:
        if not self.raw_expression or not isinstance(self.raw_expression, str):
            raise ValueError("CompatibilityRange expression must be a non-empty string.")
        object.__setattr__(self, "raw_expression", self.raw_expression.strip())

    def __str__(self) -> str:
        return self.raw_expression


@dataclass(frozen=True)
class CompatibilityResult:
    """Result of evaluating an extension or provider version against an engine/contract requirement."""
    target_name: str
    target_version: str
    required_range: CompatibilityRange
    status: CompatibilityStatus
    is_compatible: bool
    diagnostic: Optional[str] = None

    def to_dict(self) -> dict[str, str | bool | None]:
        return {
            "target_name": self.target_name,
            "target_version": self.target_version,
            "required_range": self.required_range.raw_expression,
            "status": self.status.value,
            "is_compatible": self.is_compatible,
            "diagnostic": self.diagnostic,
        }
