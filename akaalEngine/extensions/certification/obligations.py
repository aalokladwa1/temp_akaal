"""
akaalEngine.extensions.certification.obligations
================================================
Defines certification obligation domains, status categories, and data models.
Pure data-driven architecture: capabilities map directly to obligations without
hard-coded provider class hierarchies.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Mapping, Optional, Sequence


class ObligationCategory(str, Enum):
    IDENTITY_PACKAGING = "IDENTITY_PACKAGING"
    CONNECTION_SECURITY = "CONNECTION_SECURITY"
    DISCOVERY_SCHEMA = "DISCOVERY_SCHEMA"
    DATA_MOVEMENT = "DATA_MOVEMENT"
    DURABILITY = "DURABILITY"
    SEMANTICS = "SEMANTICS"
    FAILURE_HANDLING = "FAILURE_HANDLING"
    COMPATIBILITY = "COMPATIBILITY"


class ObligationStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    EXTERNAL_DEFERRED = "EXTERNAL_DEFERRED"
    UNSUPPORTED = "UNSUPPORTED"


@dataclass(frozen=True)
class ObligationResult:
    obligation_id: str
    status: ObligationStatus
    category: ObligationCategory
    diagnostic: str
    target_capability: Optional[str] = None
    details: Optional[Mapping[str, Any]] = None

    @property
    def passed(self) -> bool:
        return self.status in (
            ObligationStatus.PASS,
            ObligationStatus.NOT_APPLICABLE,
            ObligationStatus.EXTERNAL_DEFERRED,
        )


@dataclass(frozen=True)
class CertificationObligation:
    """
    An evaluation check within a certification domain.
    Applicability is driven by provider capability declarations, not provider taxonomy.
    """
    obligation_id: str
    name: str
    category: ObligationCategory
    description: str
    is_mandatory: bool = True
    trigger_capability: Optional[str] = None
    evaluator: Optional[Callable[[Any, Any], ObligationResult]] = None

    def is_applicable(self, declared_capabilities: Sequence[str]) -> bool:
        """Universal obligations (trigger_capability=None) always apply; others apply only if triggered."""
        if self.trigger_capability is None:
            return True
        norm_declared = {c.strip().upper() for c in declared_capabilities if c}
        return self.trigger_capability.strip().upper() in norm_declared
