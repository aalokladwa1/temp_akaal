"""
akaalEngine.fabric.workload_identity.gcp
===========================================
P7B.3 -- GCP IAM / Application Default Credentials / Workload Identity Federation.

Accepts injected `credentials`/`refresh_request` for testing without live GCP
infrastructure; production code should leave them unset to use
`google.auth.default()` (which itself resolves ADC / Workload Identity Federation /
service-account credentials in the standard GCP precedence order).
"""

from __future__ import annotations

from datetime import timezone
from typing import Optional

from akaalEngine.fabric.workload_identity.models import (
    CloudAuthProvider,
    CloudIdentityContext,
    WorkloadIdentityDeniedError,
    WorkloadIdentityDependencyMissing,
    WorkloadIdentityUnavailableError,
)


def resolve_gcp_workload_identity(
    project_id: Optional[str] = None,
    credentials=None,
    refresh_request=None,
) -> CloudIdentityContext:
    """
    Resolves a GCP workload identity by refreshing `credentials` (or ADC-resolved
    credentials if none supplied) and reading back its principal + expiry. `project_id`
    is accepted explicitly because ADC's own resolved project can be absent/ambiguous in
    some environments (e.g. impersonated service accounts); if not supplied, falls back to
    whatever `google.auth.default()` itself returns.
    """
    if credentials is None:
        try:
            import google.auth
        except ImportError as exc:
            raise WorkloadIdentityDependencyMissing(
                "'google-auth' is not installed; cannot resolve GCP workload identity."
            ) from exc
        try:
            credentials, discovered_project = google.auth.default()
        except Exception as exc:
            raise WorkloadIdentityUnavailableError(f"GCP Application Default Credentials unavailable: {exc}") from exc
        project_id = project_id or discovered_project

    if refresh_request is None:
        try:
            from google.auth.transport.requests import Request
            refresh_request = Request()
        except ImportError as exc:
            raise WorkloadIdentityDependencyMissing(
                "'google-auth' transport requests support is not installed."
            ) from exc

    try:
        credentials.refresh(refresh_request)
    except Exception as exc:
        msg = str(exc)
        if "invalid_grant" in msg.lower() or "permission" in msg.lower() or "denied" in msg.lower():
            raise WorkloadIdentityDeniedError(f"GCP credential refresh denied: {msg}") from exc
        raise WorkloadIdentityUnavailableError(f"GCP credential refresh failed: {msg}") from exc

    expiry = getattr(credentials, "expiry", None)
    if expiry is None:
        raise WorkloadIdentityUnavailableError("GCP credentials did not report an expiry after refresh; cannot trust it.")
    if expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)

    principal_id = (
        getattr(credentials, "service_account_email", None)
        or getattr(credentials, "signer_email", None)
        or "unresolved-principal"
    )

    if not project_id:
        raise WorkloadIdentityUnavailableError(
            "No GCP project_id could be resolved; refusing to report an identity with an "
            "unknown account boundary."
        )

    return CloudIdentityContext(
        provider=CloudAuthProvider.GCP,
        principal_id=principal_id,
        account_boundary=project_id,
        expires_at=expiry.isoformat(),
        # Round-5 hostile-review fix: GCP's real usable material is the refreshed
        # `credentials` OBJECT itself (ADC/WIF-resolved identities have no exportable
        # JSON service-account key -- that is the entire point of ADC/WIF), never a
        # plain string. Carried here exactly like AWS's temporary credentials and
        # Azure's bearer token: ephemeral, in-memory-only, never logged/serialized.
        raw_claims={"credentials_object": credentials},
    )
