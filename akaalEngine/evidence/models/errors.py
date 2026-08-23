"""
akaalEngine.evidence.models.errors
==================================
Exceptions and error types for Authority #12 — Evidence / Provenance / Execution-Truth Artifacts.
"""


class EvidenceError(Exception):
    """Base exception for Authority #12 Evidence System."""
    pass


class EvidenceIdentityError(EvidenceError):
    """Raised when migration, run, or job identity mismatch occurs."""
    pass


class EvidenceIntegrityError(EvidenceError):
    """Raised when cryptographic digest mismatch or artifact tampering is detected."""
    pass


class EvidenceFencingError(EvidenceError):
    """Raised when a stale fencing token or epoch is rejected during evidence persistence."""
    pass


class EvidenceVerificationError(EvidenceError):
    """Raised when evidence verification fails closed due to missing or invalid facts."""
    pass
