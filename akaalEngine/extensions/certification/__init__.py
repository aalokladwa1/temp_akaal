"""
akaalEngine.extensions.certification
======================================
Connector certification/conformance framework (P7A.5). Tests a resolved connector
strategy against its OWN declared capabilities -- including, mandatorily, that a
capability explicitly declared unsupported cannot be silently exercised.

Honest scope: these checks run against a strategy's live-resolved instance and its
declared metadata using only local repository state -- no live provider connection is
established. This certifies CONTRACT_CONFORMANCE (structural + declaration-integrity),
not LIVE_PROVEN behavior; a real external system is still required for that and remains
EXTERNAL_DEFERRED, exactly as declared proof levels already require.
"""

from akaalEngine.extensions.certification.models import (
    CertificationCheckResult,
    CertificationCompatibilityIdentity,
    CertificationReport,
)
from akaalEngine.extensions.certification.obligations import (
    CertificationObligation,
    ObligationCategory,
    ObligationResult,
    ObligationStatus,
)
from akaalEngine.extensions.certification.profiles import (
    CertificationProfile,
    MESSAGING_PROFILE,
    NOSQL_PROFILE,
    RELATIONAL_PROFILE,
    SAAS_PROFILE,
    STREAMING_PROFILE,
    build_profile_for_capabilities,
)
from akaalEngine.extensions.certification.runner import ConnectorCertificationRunner
from akaalEngine.extensions.truth.authority_store import (
    CertificationAuthorityStore,
    CertificationRecord,
    default_certification_authority_store,
)

__all__ = [
    "CertificationCheckResult",
    "CertificationCompatibilityIdentity",
    "CertificationReport",
    "ConnectorCertificationRunner",
    "CertificationAuthorityStore",
    "CertificationRecord",
    "default_certification_authority_store",
    "CertificationObligation",
    "ObligationCategory",
    "ObligationResult",
    "ObligationStatus",
    "CertificationProfile",
    "build_profile_for_capabilities",
    "RELATIONAL_PROFILE",
    "MESSAGING_PROFILE",
    "STREAMING_PROFILE",
    "NOSQL_PROFILE",
    "SAAS_PROFILE",
]
