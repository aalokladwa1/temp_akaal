"""
akaalEngine.evidence.models.artifact
====================================
Canonical Data Transfer Objects and Evidence Models for Authority #12.
Defines EvidenceArtifact, EvidenceManifest, EvidenceFact, EvidenceProvenance,
EvidenceDigest, EvidenceCompleteness, and EvidenceVerificationResult.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from akaalEngine.evidence.security import EvidenceSecuritySanitizer


class EvidenceCompleteness(str, Enum):
    """Machine-readable completeness classification for evidence artifacts."""
    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"
    UNPROVEN = "UNPROVEN"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class ProofClassification(str, Enum):
    """Truthful proof classification levels preserved by Authority #12."""
    IMPLEMENTED = "IMPLEMENTED"
    UNIT_PROVEN = "UNIT_PROVEN"
    INTEGRATION_PROVEN = "INTEGRATION_PROVEN"
    LIVE_PROVEN = "LIVE_PROVEN"
    SCALE_DESIGN_PROVEN = "SCALE_DESIGN_PROVEN"
    PROVIDER_SEAM = "PROVIDER_SEAM"


@dataclass
class EvidenceFact:
    """
    Individual machine-readable fact originating from an authoritative engine (#1-#11).
    Preserves authority provenance, fact type, proof classification, and quantitative value.
    """
    fact_key: str
    fact_value: Any
    originating_authority: str
    fact_type: str
    observed_at: float = 0.0
    proof_classification: ProofClassification = ProofClassification.UNIT_PROVEN
    scope: Optional[str] = None
    resource_id: Optional[str] = None

    def __repr__(self) -> str:
        raw = f"EvidenceFact(fact_key={self.fact_key!r}, fact_value={self.fact_value!r}, originating_authority={self.originating_authority!r}, fact_type={self.fact_type!r}, proof_classification={self.proof_classification!r})"
        return EvidenceSecuritySanitizer.sanitize_string(raw)

    def __str__(self) -> str:
        return self.__repr__()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "fact_key": self.fact_key,
            "fact_value": self.fact_value,
            "originating_authority": self.originating_authority,
            "fact_type": self.fact_type,
            "observed_at": self.observed_at,
            "proof_classification": self.proof_classification.value if isinstance(self.proof_classification, Enum) else str(self.proof_classification),
            "scope": self.scope,
            "resource_id": self.resource_id,
        }


@dataclass
class EvidenceProvenance:
    """
    Physical provenance metadata recording origin authority, component identity,
    and boundary/epoch identifiers.
    """
    authority_name: str
    component_id: str
    boundary_position: Optional[str] = None
    fencing_epoch: Optional[int] = None
    recorded_at: float = 0.0

    def __repr__(self) -> str:
        raw = f"EvidenceProvenance(authority_name={self.authority_name!r}, component_id={self.component_id!r}, boundary_position={self.boundary_position!r}, fencing_epoch={self.fencing_epoch!r})"
        return EvidenceSecuritySanitizer.sanitize_string(raw)

    def __str__(self) -> str:
        return self.__repr__()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "authority_name": self.authority_name,
            "component_id": self.component_id,
            "boundary_position": self.boundary_position,
            "fencing_epoch": self.fencing_epoch,
            "recorded_at": self.recorded_at,
        }


@dataclass
class EvidenceDigest:
    """
    Cryptographic integrity digest for evidence artifacts and manifests.
    Distinctly records digest algorithm, canonical payload length, and signature capability.
    """
    algorithm: str = "SHA-256"
    canonical_bytes_len: int = 0
    digest_hex: str = ""
    digital_signature_supported: bool = False
    digital_signature_status: str = "DIGEST_INTEGRITY_ONLY"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "algorithm": self.algorithm,
            "canonical_bytes_len": self.canonical_bytes_len,
            "digest_hex": self.digest_hex,
            "digital_signature_supported": self.digital_signature_supported,
            "digital_signature_status": self.digital_signature_status,
        }


@dataclass
class EvidenceArtifact:
    """
    Identity-bound evidence artifact packaging execution and validation facts.
    Guarantees cross-run isolation, deterministic serialization, and tamper detection.
    """
    artifact_id: str
    artifact_type: str
    migration_id: str
    run_id: str
    artifact_version: str = "1.0"
    job_id: Optional[str] = None
    source_identity: Optional[str] = None
    target_identity: Optional[str] = None
    provider_identity: Optional[str] = None
    plan_identity: Optional[str] = None
    validation_identity: Optional[str] = None
    cdc_boundary_position: Optional[str] = None
    fencing_epoch: Optional[int] = None
    created_at: float = 0.0
    provenance_list: List[EvidenceProvenance] = field(default_factory=list)
    facts: List[EvidenceFact] = field(default_factory=list)
    digest: Optional[EvidenceDigest] = None
    completeness: EvidenceCompleteness = EvidenceCompleteness.UNPROVEN

    def __repr__(self) -> str:
        raw = f"EvidenceArtifact(artifact_id={self.artifact_id!r}, artifact_type={self.artifact_type!r}, migration_id={self.migration_id!r}, run_id={self.run_id!r}, completeness={self.completeness!r}, facts_count={len(self.facts)})"
        return EvidenceSecuritySanitizer.sanitize_string(raw)

    def __str__(self) -> str:
        return self.__repr__()

    def to_dict(self, include_digest: bool = True) -> Dict[str, Any]:
        payload = {
            "artifact_id": self.artifact_id,
            "artifact_type": self.artifact_type,
            "artifact_version": self.artifact_version,
            "migration_id": self.migration_id,
            "run_id": self.run_id,
            "job_id": self.job_id,
            "source_identity": self.source_identity,
            "target_identity": self.target_identity,
            "provider_identity": self.provider_identity,
            "plan_identity": self.plan_identity,
            "validation_identity": self.validation_identity,
            "cdc_boundary_position": self.cdc_boundary_position,
            "fencing_epoch": self.fencing_epoch,
            "created_at": self.created_at,
            "completeness": self.completeness.value if isinstance(self.completeness, Enum) else str(self.completeness),
            "provenance_list": [p.to_dict() for p in self.provenance_list],
            "facts": [f.to_dict() for f in self.facts],
        }
        if include_digest and self.digest:
            payload["digest"] = self.digest.to_dict()
        return payload


@dataclass
class EvidenceManifest:
    """
    Binds related EvidenceArtifact objects into a single deterministic bundle for a migration run.
    """
    manifest_id: str
    migration_id: str
    run_id: str
    created_at: float = 0.0
    artifacts: List[EvidenceArtifact] = field(default_factory=list)
    completeness: EvidenceCompleteness = EvidenceCompleteness.UNPROVEN
    manifest_digest: Optional[EvidenceDigest] = None

    def __repr__(self) -> str:
        raw = f"EvidenceManifest(manifest_id={self.manifest_id!r}, migration_id={self.migration_id!r}, run_id={self.run_id!r}, completeness={self.completeness!r}, artifact_count={len(self.artifacts)})"
        return EvidenceSecuritySanitizer.sanitize_string(raw)

    def __str__(self) -> str:
        return self.__repr__()

    def to_dict(self, include_digest: bool = True) -> Dict[str, Any]:
        payload = {
            "manifest_id": self.manifest_id,
            "migration_id": self.migration_id,
            "run_id": self.run_id,
            "created_at": self.created_at,
            "completeness": self.completeness.value if isinstance(self.completeness, Enum) else str(self.completeness),
            "artifacts": [a.to_dict(include_digest=True) for a in self.artifacts],
        }
        if include_digest and self.manifest_digest:
            payload["manifest_digest"] = self.manifest_digest.to_dict()
        return payload


@dataclass
class EvidenceVerificationResult:
    """
    Deterministic verification result for an evidence artifact or manifest.
    Reports tamper status, boundary freshness, completeness, and rejection reasons.
    """
    is_valid: bool
    migration_id: str
    run_id: str
    completeness: EvidenceCompleteness
    verified_artifact_count: int = 0
    tamper_detected: bool = False
    boundary_fresh: bool = True
    reasons: List[str] = field(default_factory=list)

    def __repr__(self) -> str:
        raw = f"EvidenceVerificationResult(is_valid={self.is_valid}, migration_id={self.migration_id!r}, run_id={self.run_id!r}, completeness={self.completeness!r}, verified_artifact_count={self.verified_artifact_count}, tamper_detected={self.tamper_detected}, boundary_fresh={self.boundary_fresh})"
        return EvidenceSecuritySanitizer.sanitize_string(raw)

    def __str__(self) -> str:
        return self.__repr__()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "migration_id": self.migration_id,
            "run_id": self.run_id,
            "completeness": self.completeness.value if isinstance(self.completeness, Enum) else str(self.completeness),
            "verified_artifact_count": self.verified_artifact_count,
            "tamper_detected": self.tamper_detected,
            "boundary_fresh": self.boundary_fresh,
            "reasons": list(self.reasons),
        }
