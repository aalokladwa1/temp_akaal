"""
akaalEngine.extensions.dependencies.diagnostics
===============================================
Consolidated diagnostic report aggregator for dependency inspection across extensions and provider strategies.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from akaalEngine.extensions.models.dependency import DependencyDiagnostic, DependencyStatus


@dataclass(frozen=True)
class DependencyDiagnosticReport:
    """Consolidated diagnostic report of all inspected dependencies for a target."""
    target_id: str
    diagnostics: Sequence[DependencyDiagnostic] = field(default_factory=tuple)

    @property
    def is_all_mandatory_satisfied(self) -> bool:
        """Returns True if all non-optional dependencies are satisfied."""
        for d in self.diagnostics:
            if not d.is_optional and not d.is_satisfied:
                return False
        return True

    @property
    def missing_mandatory(self) -> Sequence[DependencyDiagnostic]:
        return tuple(d for d in self.diagnostics if not d.is_optional and not d.is_satisfied)

    @property
    def missing_optional(self) -> Sequence[DependencyDiagnostic]:
        return tuple(d for d in self.diagnostics if d.is_optional and not d.is_satisfied)

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_id": self.target_id,
            "is_all_mandatory_satisfied": self.is_all_mandatory_satisfied,
            "missing_mandatory": [d.to_dict() for d in self.missing_mandatory],
            "missing_optional": [d.to_dict() for d in self.missing_optional],
            "all_diagnostics": [d.to_dict() for d in self.diagnostics],
        }
