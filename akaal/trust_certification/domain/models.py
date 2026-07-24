"""
AKAAL Platform 11 — Enterprise Trust & Certification Domain Models.
"""

from dataclasses import dataclass
from typing import List, Dict, Any
from akaal.trust_certification.domain.enums import TrustGrade, CertificationSealStatus


@dataclass(frozen=True)
class ValidationLedgerEntry:
    entry_id: str
    index: int
    timestamp: str
    previous_hash: str
    validation_payload: Dict[str, Any]
    block_hash: str


@dataclass(frozen=True)
class MigrationTrustScore:
    target_migration_id: str
    trust_score: float  # 0.0 - 100.0
    grade: TrustGrade
    calculated_at: str


@dataclass(frozen=True)
class EnterpriseCertificationReport:
    report_id: str
    target_migration_id: str
    trust_score: float
    grade: TrustGrade
    certified_by: str
    issued_at: str
    certificate_uri: str


@dataclass(frozen=True)
class ComplianceEvidencePackage:
    package_id: str
    target_migration_id: str
    evidence_items: List[Dict[str, Any]]
    package_hash: str
    created_at: str


@dataclass(frozen=True)
class DigitalCertificationSeal:
    seal_id: str
    target_migration_id: str
    seal_signature: str
    status: CertificationSealStatus
    issued_at: str


@dataclass(frozen=True)
class AuditExportPackage:
    export_id: str
    target_migration_id: str
    archive_format: str
    export_hash: str
    exported_at: str
