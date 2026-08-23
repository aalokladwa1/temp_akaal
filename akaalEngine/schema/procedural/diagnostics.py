"""
akaalEngine.schema.procedural.diagnostics
=========================================
Procedural conversion lifecycle state, diagnostics tracker, and source mapping.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Any, List, Mapping, Optional, Tuple

from akaalEngine.schema.procedural.lexer import SourceLocation


class ConversionState(str, Enum):
    """Audited procedural conversion progression states."""
    PARSED = "PARSED"
    ANALYZED = "ANALYZED"
    TRANSPILED = "TRANSPILED"
    SYNTACTICALLY_CHECKED = "SYNTACTICALLY_CHECKED"
    COMPATIBILITY_WRAPPED = "COMPATIBILITY_WRAPPED"
    MANUAL_REVIEW_REQUIRED = "MANUAL_REVIEW_REQUIRED"


@dataclass(frozen=True)
class ProceduralDiagnostic:
    """A diagnostic issue, warning, or unsupported construct discovered during procedural conversion."""
    severity: str  # ERROR, WARNING, INFO, MANUAL_INTERVENTION
    category: str
    message: str
    location: Optional[SourceLocation] = None
    source_snippet: Optional[str] = None
    suggested_remediation: Optional[str] = None


@dataclass(frozen=True)
class ProceduralConversionResult:
    """Result of routine transpilation including target SQL, diagnostics, and lifecycle state."""
    routine_name: str
    target_engine: str
    state: ConversionState
    target_sql: str
    diagnostics: Tuple[ProceduralDiagnostic, ...] = field(default_factory=tuple)
    required_compat_helpers: Tuple[str, ...] = field(default_factory=tuple)
    extra: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))

    def __post_init__(self) -> None:
        if not isinstance(self.diagnostics, tuple):
            object.__setattr__(self, "diagnostics", tuple(self.diagnostics))
        if not isinstance(self.required_compat_helpers, tuple):
            object.__setattr__(self, "required_compat_helpers", tuple(self.required_compat_helpers))
        if not isinstance(self.extra, MappingProxyType):
            object.__setattr__(self, "extra", MappingProxyType(dict(self.extra)))

    @property
    def has_errors(self) -> bool:
        return any(d.severity in ("ERROR", "MANUAL_INTERVENTION") for d in self.diagnostics)

    def to_dict(self) -> dict[str, Any]:
        return {
            "routine_name": self.routine_name,
            "target_engine": self.target_engine,
            "state": self.state.value,
            "target_sql": self.target_sql,
            "diagnostics": [
                {
                    "severity": d.severity,
                    "category": d.category,
                    "message": d.message,
                    "location": str(d.location) if d.location else None,
                    "source_snippet": d.source_snippet,
                    "suggested_remediation": d.suggested_remediation,
                }
                for d in self.diagnostics
            ],
            "required_compat_helpers": list(self.required_compat_helpers),
            "extra": dict(self.extra),
        }
