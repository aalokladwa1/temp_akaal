"""
AKAAL P2.10 / P2.10.1 — Canonical Reporting, Certification & Governance Evidence Models
========================================================================================
Immutable domain models for Canonical Reports, Certification Artifacts, Evidence Manifests,
Certification Claims, and Tamper-Evident Fingerprints.
"""

from dataclasses import dataclass, field
from enum import Enum
import hashlib
import json
from typing import Any, Dict, List, Optional

SERIALIZATION_VERSION = "AKAAL-CANONICAL-V1"


class CanonicalReportType(str, Enum):
    """Canonical report type classification."""
    MIGRATION = "MIGRATION"
    VALIDATION_ONLY = "VALIDATION_ONLY"
    RECONCILIATION = "RECONCILIATION"
    SCHEMA_ASSESSMENT = "SCHEMA_ASSESSMENT"
    SCHEMA_DRIFT = "SCHEMA_DRIFT"
    MIGRATION_AND_VALIDATION = "MIGRATION_AND_VALIDATION"


class CertificationOutcome(str, Enum):
    """Certification status classification."""
    CERTIFIED = "CERTIFIED"
    CERTIFIED_WITH_WARNINGS = "CERTIFIED_WITH_WARNINGS"
    NOT_CERTIFIED = "NOT_CERTIFIED"
    INDETERMINATE = "INDETERMINATE"


class CertificationClaimType(str, Enum):
    """Explicit certification claim classification."""
    SCHEMA_COMPATIBILITY_VERIFIED = "SCHEMA_COMPATIBILITY_VERIFIED"
    ROW_COUNT_VERIFIED = "ROW_COUNT_VERIFIED"
    CANONICAL_CHECKSUM_VERIFIED = "CANONICAL_CHECKSUM_VERIFIED"
    MERKLE_ROOT_VERIFIED = "MERKLE_ROOT_VERIFIED"
    ROW_RECONCILIATION_VERIFIED = "ROW_RECONCILIATION_VERIFIED"
    NO_SOURCE_ONLY_ROWS = "NO_SOURCE_ONLY_ROWS"
    NO_TARGET_ONLY_ROWS = "NO_TARGET_ONLY_ROWS"
    NO_VALUE_MISMATCHES = "NO_VALUE_MISMATCHES"
    PROGRAMMABLE_OBJECTS_VERIFIED = "PROGRAMMABLE_OBJECTS_VERIFIED"
    GOVERNANCE_APPROVAL_COMPLETE = "GOVERNANCE_APPROVAL_COMPLETE"


@dataclass(frozen=True)
class EvidenceManifestItem:
    """Entry in tamper-evident evidence manifest."""
    evidence_type: str
    authority: str
    version: str
    fingerprint: str
    status: str
    scope: str


@dataclass(frozen=True)
class CertificationClaim:
    """Individual evidence-derived certification claim."""
    claim_type: CertificationClaimType
    status: str  # "PASSED", "WARNING", "FAILED"
    evidence_fingerprint: str
    description: str


@dataclass(frozen=True)
class CertificationArtifact:
    """Tamper-evident Enterprise Certification Artifact."""
    certification_id: str
    report_id: str
    job_id: str = ""
    run_id: str = ""
    outcome: CertificationOutcome = CertificationOutcome.NOT_CERTIFIED
    claims: List[CertificationClaim] = field(default_factory=list)
    evidence_manifest: List[EvidenceManifestItem] = field(default_factory=list)
    issued_at: str = ""
    issuer: str = "AKAAL Enterprise Governance Authority v1.0"
    certification_fingerprint: str = ""

    def compute_fingerprint(self) -> str:
        """Computes deterministic SHA-256 fingerprint over logical evidence payload and job/run binding."""
        claims_data = [f"{c.claim_type.value}:{c.status}:{c.evidence_fingerprint}" for c in sorted(self.claims, key=lambda x: x.claim_type.value)]
        manifest_data = [f"{m.evidence_type}:{m.fingerprint}:{m.status}" for m in sorted(self.evidence_manifest, key=lambda x: x.evidence_type)]

        raw_payload = f"{self.certification_id}:{self.report_id}:{self.job_id}:{self.run_id}:{self.outcome.value}:{','.join(claims_data)}:{','.join(manifest_data)}:{SERIALIZATION_VERSION}"
        return hashlib.sha256(raw_payload.encode("utf-8")).hexdigest()

    def verify_integrity(self) -> bool:
        """Verifies tamper-evidence fingerprint against current artifact contents."""
        return self.certification_fingerprint == self.compute_fingerprint()


@dataclass
class CanonicalReport:
    """Canonical Enterprise Report Representation."""
    report_id: str
    report_version: str
    report_type: CanonicalReportType
    job_id: str
    run_id: str
    created_at: str
    source_info: Dict[str, Any]
    target_info: Dict[str, Any]
    execution_summary: Dict[str, Any]
    schema_summary: Dict[str, Any]
    data_summary: Dict[str, Any]
    validation_summary: Dict[str, Any]
    governance_summary: Dict[str, Any]
    warnings: List[str]
    errors: List[str]
    manual_review_items: List[str]
    evidence_fingerprints: List[str]
    final_outcome: str
    certification: Optional[CertificationArtifact] = None
    report_fingerprint: str = ""

    def compute_report_fingerprint(self) -> str:
        """Computes deterministic SHA-256 report fingerprint."""
        raw_payload = (
            f"{self.report_id}:{self.job_id}:{self.run_id}:{self.report_type.value}:"
            f"{self.final_outcome}:{len(self.warnings)}:{len(self.errors)}:{SERIALIZATION_VERSION}"
        )
        return hashlib.sha256(raw_payload.encode("utf-8")).hexdigest()

    def to_json(self) -> str:
        """Exports report as canonical, versioned machine-readable JSON."""
        d = {
            "report_id": self.report_id,
            "report_version": self.report_version,
            "report_type": self.report_type.value,
            "job_id": self.job_id,
            "run_id": self.run_id,
            "created_at": self.created_at,
            "source_info": self.source_info,
            "target_info": self.target_info,
            "execution_summary": self.execution_summary,
            "schema_summary": self.schema_summary,
            "data_summary": self.data_summary,
            "validation_summary": self.validation_summary,
            "governance_summary": self.governance_summary,
            "warnings": self.warnings,
            "errors": self.errors,
            "manual_review_items": self.manual_review_items,
            "evidence_fingerprints": self.evidence_fingerprints,
            "final_outcome": self.final_outcome,
            "report_fingerprint": self.report_fingerprint,
        }
        if self.certification:
            d["certification"] = {
                "certification_id": self.certification.certification_id,
                "job_id": self.certification.job_id,
                "run_id": self.certification.run_id,
                "outcome": self.certification.outcome.value,
                "certification_fingerprint": self.certification.certification_fingerprint,
                "claims": [{"claim_type": c.claim_type.value, "status": c.status, "description": c.description} for c in self.certification.claims],
                "evidence_manifest": [{"type": m.evidence_type, "fingerprint": m.fingerprint, "status": m.status} for m in self.certification.evidence_manifest],
            }

        return json.dumps(d, sort_keys=True, indent=2)
