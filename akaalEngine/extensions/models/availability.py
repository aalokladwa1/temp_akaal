"""
akaalEngine.extensions.models.availability
==========================================
Models representing extension and provider runtime availability status.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Optional, Sequence

from akaalEngine.extensions.models.dependency import DependencyDiagnostic
from akaalEngine.extensions.models.enums import ExtensionLifecycleState
from akaalEngine.extensions.models.identity import ExtensionId, ProviderId


@dataclass(frozen=True)
class ExtensionAvailability:
    """Consolidated availability status for an extension or provider."""
    is_available: bool
    lifecycle_state: ExtensionLifecycleState
    dependency_satisfied: bool
    missing_mandatory_dependencies: Sequence[str] = field(default_factory=tuple)
    missing_optional_dependencies: Sequence[str] = field(default_factory=tuple)
    diagnostics: Sequence[DependencyDiagnostic] = field(default_factory=tuple)
    reason: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_available": self.is_available,
            "lifecycle_state": self.lifecycle_state.value,
            "dependency_satisfied": self.dependency_satisfied,
            "missing_mandatory_dependencies": list(self.missing_mandatory_dependencies),
            "missing_optional_dependencies": list(self.missing_optional_dependencies),
            "diagnostics": [d.to_dict() for d in self.diagnostics],
            "reason": self.reason,
        }
