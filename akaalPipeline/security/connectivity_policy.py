"""akaalPipeline.security.connectivity_policy
==========================================
P7.9 connectivity policy vocabulary, re-exported from its authoritative implementation.

CORRECTION (hostile review): the real enforcement logic was relocated to
akaalEngine.connection.security.connectivity_policy because it operates exclusively on
Engine's own physical connection descriptor types (TLSBinding/RouteSpec) and must run
directly on Engine's authoritative connection-establishment path
(akaalEngine.connection.sessions.factory.SessionFactory) to be enforced rather than
merely composable in tests. Pipeline-side policy authors (governance/plan-compilation
code that decides *which* ConnectivityRequirement a migration needs) may still import
the vocabulary from here without duplicating it or reversing the Pipeline->Engine
dependency direction that akaalPipeline importing akaalEngine's connection models would
otherwise create.
"""

from __future__ import annotations

from akaalEngine.connection.security.connectivity_policy import (
    ConnectivityComplianceReport,
    ConnectivityPolicyEnforcer,
    ConnectivityPolicyViolationError,
    ConnectivityRequirement,
)

__all__ = [
    "ConnectivityComplianceReport",
    "ConnectivityPolicyEnforcer",
    "ConnectivityPolicyViolationError",
    "ConnectivityRequirement",
]
