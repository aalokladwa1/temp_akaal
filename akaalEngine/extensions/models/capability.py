"""
akaalEngine.extensions.models.capability
========================================
Models for declared capabilities and derived capability truth.
Extensions ensures UNKNOWN never evaluates to SUPPORTED and self-declarations cannot self-award live certification.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Optional, Sequence

from akaalEngine.extensions.models.enums import ProofLevel


@dataclass(frozen=True)
class CapabilityDeclaration:
    """A declared capability assertion within an extension or provider manifest."""
    capability_name: str
    is_supported: bool = True
    declared_proof_level: ProofLevel = ProofLevel.DECLARED
    required_dependencies: Sequence[str] = field(default_factory=tuple)
    restrictions: Sequence[str] = field(default_factory=tuple)
    notes: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.capability_name or not isinstance(self.capability_name, str):
            raise ValueError("CapabilityDeclaration capability_name must be a non-empty string.")
        object.__setattr__(self, "capability_name", self.capability_name.strip().upper())
        object.__setattr__(
            self,
            "required_dependencies",
            tuple(self.required_dependencies) if self.required_dependencies else (),
        )
        object.__setattr__(
            self,
            "restrictions",
            tuple(self.restrictions) if self.restrictions else (),
        )


@dataclass(frozen=True)
class CapabilityTruth:
    """
    Authoritative derived capability truth.
    Evaluated from manifest declaration + concrete implementation + dependency satisfaction + proof governance.
    """
    capability_name: str
    is_supported: bool
    proof_level: ProofLevel
    is_dependency_satisfied: bool
    missing_dependencies: Sequence[str] = field(default_factory=tuple)
    restrictions: Sequence[str] = field(default_factory=tuple)
    diagnostic: Optional[str] = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "missing_dependencies",
            tuple(self.missing_dependencies) if self.missing_dependencies else (),
        )
        object.__setattr__(
            self,
            "restrictions",
            tuple(self.restrictions) if self.restrictions else (),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "capability_name": self.capability_name,
            "is_supported": self.is_supported,
            "proof_level": self.proof_level.value,
            "is_dependency_satisfied": self.is_dependency_satisfied,
            "missing_dependencies": list(self.missing_dependencies),
            "restrictions": list(self.restrictions),
            "diagnostic": self.diagnostic,
        }
