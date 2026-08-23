"""
akaalEngine.extensions.models.proof
===================================
Models for capability proof references, external test evidence pointers, and trusted certifications.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Optional, Sequence

from akaalEngine.extensions.models.enums import ProofLevel


import types


@dataclass(frozen=True)
class ProofReference:
    """Provenance pointer to automated test, benchmark, or emulator verification evidence."""
    proof_id: str
    target_capability: str
    proven_level: ProofLevel
    test_suite_ref: str
    verified_at: str
    verifier_identity: str
    evidence_metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.proof_id or not isinstance(self.proof_id, str):
            raise ValueError("ProofReference proof_id must be a non-empty string.")
        if not self.target_capability or not isinstance(self.target_capability, str):
            raise ValueError("ProofReference target_capability must be a non-empty string.")
        object.__setattr__(
            self,
            "evidence_metadata",
            types.MappingProxyType(dict(self.evidence_metadata)) if self.evidence_metadata else types.MappingProxyType({}),
        )


@dataclass(frozen=True)
class CertificationReference:
    """Provenance pointer to formal live-database or partner certification."""
    certification_id: str
    certifier_authority: str
    certified_level: ProofLevel
    certified_target: str
    valid_from: str
    valid_until: Optional[str] = None
    signature_fingerprint: Optional[str] = None
    audit_dossier_ref: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.certification_id or not isinstance(self.certification_id, str):
            raise ValueError("CertificationReference certification_id must be a non-empty string.")
