"""
akaalEngine.fabric.workload_identity.boundary
================================================
P7B.3 -- The ONLY sanctioned path from a cloud-authenticated identity to an AKAAL
authorization decision.

This module makes NO authorization decision of its own. It exists specifically to make
the "cloud authentication != AKAAL authorization" law structurally unbypassable:
`CloudAuthenticationBoundary.authorize_akaal_action` always delegates the actual yes/no
decision to a caller-supplied `AKAALAuthorizationCallback` -- in production this callback
wraps `akaalPipeline.security.central_authorization.CentralAuthorizationEngine` (this
module intentionally does not import akaalPipeline directly, preserving the established
Pipeline -> Engine dependency direction; Pipeline-side code constructs the callback and
passes it in). There is no default-allow path: a missing callback, an expired identity,
or a non-boolean callback return all fail closed.
"""

from __future__ import annotations

from typing import Any, Mapping, Optional, Protocol, runtime_checkable

from akaalEngine.fabric.workload_identity.models import (
    CloudIdentityContext,
    WorkloadIdentityError,
    WorkloadIdentityExpiredError,
)


@runtime_checkable
class AKAALAuthorizationCallback(Protocol):
    """
    Callable contract for the actual AKAAL authorization decision. Production callers
    should implement this by wrapping their own CentralAuthorizationEngine (or equivalent)
    decision entry point -- never by returning a hardcoded True.
    """

    def __call__(
        self,
        cloud_identity: CloudIdentityContext,
        requested_action: str,
        context: Mapping[str, Any],
    ) -> bool:
        ...


class CloudAuthenticationBoundary:
    """Fail-closed boundary between cloud IAM authentication and AKAAL authorization."""

    def authorize_akaal_action(
        self,
        cloud_identity: CloudIdentityContext,
        requested_action: str,
        authorization_callback: Optional[AKAALAuthorizationCallback],
        context: Optional[Mapping[str, Any]] = None,
    ) -> bool:
        if not requested_action or not requested_action.strip():
            raise WorkloadIdentityError("requested_action must be a non-empty string.")

        if cloud_identity.is_expired():
            raise WorkloadIdentityExpiredError(
                f"Cloud identity {cloud_identity.principal_id!r} has expired at "
                f"{cloud_identity.expires_at!r}; refusing to authorize {requested_action!r}."
            )

        if authorization_callback is None:
            raise WorkloadIdentityError(
                "No AKAALAuthorizationCallback supplied. A successfully authenticated cloud "
                "identity can NEVER be treated as AKAAL-authorized on its own -- the caller "
                "must supply the actual AKAAL authorization decision function."
            )

        decision = authorization_callback(cloud_identity, requested_action, context or {})
        if not isinstance(decision, bool):
            raise WorkloadIdentityError(
                f"AKAALAuthorizationCallback for {requested_action!r} returned a non-boolean "
                f"value ({decision!r}); ambiguous authorization decisions fail closed."
            )
        return decision


def is_cloud_identity_usable(identity: Optional[CloudIdentityContext]) -> bool:
    """
    Ready-made truthful check for whether an attached CloudIdentityContext (e.g. under
    credentials["cloud_identity"] as populated by
    akaalEngine.connection.security.authentication.CloudIAMAuthenticationHandler) is
    even worth considering for an authorization decision: present AND not expired.

    IMPORTANT: returning True here is NOT authorization -- it only means "this identity
    is not obviously unusable". Callers must still route through
    CloudAuthenticationBoundary.authorize_akaal_action (or an equivalent real AKAAL
    authorization check) before treating the identity as sufficient for anything.
    Provided so the first real caller that wants to gate on identity freshness has a
    correct primitive rather than reinventing (or omitting) one, matching the existing
    repository pattern in akaalPipeline.security.kms_provider.require_key_tenant_match.
    """
    if identity is None:
        return False
    return not identity.is_expired()


default_cloud_authentication_boundary = CloudAuthenticationBoundary()
