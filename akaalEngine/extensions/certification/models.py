"""
akaalEngine.extensions.certification.models
==============================================
Result types and aggregation models for connector certification runs.
Implements non-Boolean status aggregation and proof level preservation:
PASS, FAIL, NOT_APPLICABLE, EXTERNAL_DEFERRED, UNSUPPORTED.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Optional, Sequence

from akaalEngine.extensions.certification.obligations import (
    ObligationCategory,
    ObligationResult,
    ObligationStatus,
)
from akaalEngine.extensions.models.enums import ProofLevel


@dataclass(frozen=True)
class CertificationCheckResult:
    """Legacy check result container for backward compatibility."""
    check_name: str
    passed: bool
    category: str
    diagnostic: str
    capability_name: Optional[str] = None
    status: ObligationStatus = ObligationStatus.PASS

    def __post_init__(self) -> None:
        if not self.passed and self.status == ObligationStatus.PASS:
            object.__setattr__(self, "status", ObligationStatus.FAIL)


@dataclass(frozen=True)
class CertificationCompatibilityIdentity:
    """Authoritative identity dimensions binding a certification."""
    akaal_version_range: str
    extension_id: str
    extension_version: str
    provider_id: str
    capability_name: str
    provider_version_range: Optional[str] = None
    strategy_id: Optional[str] = None
    certified_level: ProofLevel = ProofLevel.INTEGRATION_PROVEN


@dataclass(frozen=True)
class CertificationReport:
    provider_id: str
    authority_id: str
    strategy_id: str
    results: Sequence[CertificationCheckResult] = field(default_factory=tuple)
    obligation_results: Sequence[ObligationResult] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "results", tuple(self.results))
        object.__setattr__(self, "obligation_results", tuple(self.obligation_results))

    @property
    def passed(self) -> bool:
        """
        True only if:
        1. At least one check/obligation was evaluated.
        2. Zero mandatory checks have status FAIL.
        3. Zero checks have status UNSUPPORTED when capability was advertised.
        """
        if not self.results and not self.obligation_results:
            return False

        for r in self.results:
            if not r.passed:
                return False

        for ob_res in self.obligation_results:
            if ob_res.status in (ObligationStatus.FAIL, ObligationStatus.UNSUPPORTED):
                return False

        return True

    @property
    def has_external_deferred(self) -> bool:
        return any(
            r.status == ObligationStatus.EXTERNAL_DEFERRED
            for r in self.obligation_results
        )

    @property
    def allowable_proof_level(self) -> ProofLevel:
        """
        Preserves proof level ceiling:
        If any obligation is EXTERNAL_DEFERRED, proof level CANNOT be LIVE_PROVEN.
        """
        if not self.passed:
            return ProofLevel.DECLARED
        if self.has_external_deferred:
            return ProofLevel.INTEGRATION_PROVEN
        return ProofLevel.LIVE_PROVEN

    @property
    def failed_checks(self) -> Sequence[CertificationCheckResult]:
        return tuple(r for r in self.results if not r.passed)

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "authority_id": self.authority_id,
            "strategy_id": self.strategy_id,
            "passed": self.passed,
            "allowable_proof_level": self.allowable_proof_level.value,
            "has_external_deferred": self.has_external_deferred,
            "results": [
                {
                    "check_name": r.check_name,
                    "passed": r.passed,
                    "category": r.category,
                    "diagnostic": r.diagnostic,
                    "capability_name": r.capability_name,
                    "status": r.status.value,
                }
                for r in self.results
            ],
            "obligation_results": [
                {
                    "obligation_id": o.obligation_id,
                    "category": o.category.value,
                    "status": o.status.value,
                    "diagnostic": o.diagnostic,
                    "target_capability": o.target_capability,
                }
                for o in self.obligation_results
            ],
        }
