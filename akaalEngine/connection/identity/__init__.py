"""
akaalEngine.connection.identity
===============================
Identity attestation, deterministic secret-free fingerprinting, and drift detection.
"""

from akaalEngine.connection.identity.fingerprint import (
    canonicalize_endpoint_spec,
    compute_endpoint_fingerprint,
)

from akaalEngine.connection.identity.attestation import (
    IdentityAttestor,
)

from akaalEngine.connection.identity.drift import (
    DriftDetector,
)

__all__ = [
    "canonicalize_endpoint_spec",
    "compute_endpoint_fingerprint",
    "IdentityAttestor",
    "DriftDetector",
]
