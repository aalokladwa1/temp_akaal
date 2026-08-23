"""
akaalEngine.evidence
====================
Authority #12 — Evidence / Provenance / Execution-Truth Artifacts.
Canonical public exports for EvidenceAuthority, models, and exceptions.
"""

from akaalEngine.evidence.api import EvidenceAuthority
from akaalEngine.evidence.canonical import CanonicalEvidenceSerializer, EvidenceDigestCalculator
from akaalEngine.evidence.models import (
    EvidenceArtifact,
    EvidenceCompleteness,
    EvidenceDigest,
    EvidenceError,
    EvidenceFact,
    EvidenceFencingError,
    EvidenceIdentityError,
    EvidenceIntegrityError,
    EvidenceManifest,
    EvidenceProvenance,
    EvidenceVerificationError,
    EvidenceVerificationResult,
    ProofClassification,
)
from akaalEngine.evidence.security import EvidenceSecuritySanitizer
from akaalEngine.evidence.verification import EvidenceVerificationEngine

__all__ = [
    "EvidenceAuthority",
    "CanonicalEvidenceSerializer",
    "EvidenceDigestCalculator",
    "EvidenceArtifact",
    "EvidenceCompleteness",
    "EvidenceDigest",
    "EvidenceError",
    "EvidenceFact",
    "EvidenceFencingError",
    "EvidenceIdentityError",
    "EvidenceIntegrityError",
    "EvidenceManifest",
    "EvidenceProvenance",
    "EvidenceVerificationError",
    "EvidenceVerificationResult",
    "ProofClassification",
    "EvidenceSecuritySanitizer",
    "EvidenceVerificationEngine",
]
