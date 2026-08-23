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

from akaalEngine.schema.models.types import freeze_deep
from akaalEngine.schema.procedural.lexer import SourceLocation


class ConversionState(str, Enum):
    """Audited procedural conversion progression states."""
    PARSED = "PARSED"
    ANALYZED = "ANALYZED"
    TRANSPILED = "TRANSPILED"
    SYNTACTICALLY_CHECKED = "SYNTACTICALLY_CHECKED"
    COMPATIBILITY_WRAPPED = "COMPATIBILITY_WRAPPED"
    MANUAL_REVIEW_REQUIRED = "MANUAL_REVIEW_REQUIRED"
    MANUAL_REWRITE_REQUIRED = "MANUAL_REWRITE_REQUIRED"
    CONVERTED = "CONVERTED"
    FAILED = "FAILED"


@dataclass(frozen=True)
class ProceduralDiagnostic:
    """A diagnostic issue, warning, or unsupported construct discovered during procedural conversion."""
    severity: str  # ERROR, WARNING, INFO, MANUAL_INTERVENTION
    category: str = "GENERAL"
    message: str = ""
    location: Optional[SourceLocation] = None
    source_snippet: Optional[str] = None
    suggested_remediation: Optional[str] = None
    rule: Optional[str] = None
    line: Optional[int] = None
    column: Optional[int] = None


@dataclass(frozen=True)
class ProceduralConversionResult:
    """Result of routine transpilation including target SQL, diagnostics, and lifecycle state."""
    routine_name: str
    target_engine: str = "POSTGRESQL"
    state: ConversionState = ConversionState.TRANSPILED
    target_sql: str = ""
    conversion_state: Optional[ConversionState] = None
    emitted_sql: Optional[str] = None
    diagnostics: Tuple[ProceduralDiagnostic, ...] = field(default_factory=tuple)
    required_compat_helpers: Tuple[str, ...] = field(default_factory=tuple)
    source_dialect: Optional[str] = None
    target_dialect: Optional[str] = None
    warnings: Tuple[str, ...] = field(default_factory=tuple)
    extra: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))

    def __post_init__(self) -> None:
        if self.conversion_state is not None and self.state == ConversionState.TRANSPILED:
            object.__setattr__(self, "state", self.conversion_state)
        elif self.conversion_state is None:
            object.__setattr__(self, "conversion_state", self.state)

        if self.emitted_sql is not None and not self.target_sql:
            object.__setattr__(self, "target_sql", self.emitted_sql)
        elif self.emitted_sql is None:
            object.__setattr__(self, "emitted_sql", self.target_sql)

        if not isinstance(self.diagnostics, tuple):
            object.__setattr__(self, "diagnostics", tuple(self.diagnostics))
        if not isinstance(self.required_compat_helpers, tuple):
            object.__setattr__(self, "required_compat_helpers", tuple(self.required_compat_helpers))
        if not isinstance(self.warnings, tuple):
            object.__setattr__(self, "warnings", tuple(self.warnings))
        object.__setattr__(self, "extra", freeze_deep(self.extra))

    @property
    def has_errors(self) -> bool:
        return any(d.severity in ("ERROR", "MANUAL_INTERVENTION") for d in self.diagnostics)

    def to_dict(self) -> dict[str, Any]:
        return {
            "routine_name": self.routine_name,
            "target_engine": self.target_engine,
            "state": self.state.value,
            "conversion_state": self.state.value,
            "target_sql": self.target_sql,
            "emitted_sql": self.target_sql,
            "diagnostics": [
                {
                    "severity": d.severity,
                    "category": d.category,
                    "message": d.message,
                    "location": str(d.location) if d.location else None,
                    "suggested_remediation": d.suggested_remediation,
                    "rule": d.rule,
                }
                for d in self.diagnostics
            ],
            "required_compat_helpers": list(self.required_compat_helpers),
            "warnings": list(self.warnings),
            "extra": dict(self.extra),
        }
