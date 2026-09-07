"""
akaalEngine.fabric.workload_identity.azure
=============================================
P7B.3 -- Azure Entra ID / Managed Identity / workload identity token resolution.

Accepts an injected `credential` object exposing `.get_token(scope) -> token` (the
azure-identity `TokenCredential` protocol shape) for testing without live Azure
infrastructure; production code should leave it unset to use
`azure.identity.DefaultAzureCredential` (which itself resolves Managed
Identity/workload-identity/environment credentials in the standard Azure precedence
order).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from akaalEngine.fabric.workload_identity.models import (
    CloudAuthProvider,
    CloudIdentityContext,
    WorkloadIdentityDeniedError,
    WorkloadIdentityDependencyMissing,
    WorkloadIdentityUnavailableError,
)

DEFAULT_SCOPE = "https://management.azure.com/.default"


def resolve_azure_workload_identity(
    subscription_id: str,
    credential=None,
    scope: str = DEFAULT_SCOPE,
    principal_id: Optional[str] = None,
) -> CloudIdentityContext:
    """
    Resolves an Azure workload identity by requesting a real access token from `credential`
    (or a fresh `DefaultAzureCredential` if none is supplied). `subscription_id` is required
    explicitly -- an Azure access token does not itself carry the target subscription, and
    this function must never guess or silently default one. `principal_id`, if not supplied,
    is best-effort left as "unresolved-principal" (decoding the object id out of the token
    would require JWT parsing this module deliberately does not duplicate; callers that need
    the exact principal should resolve it via Microsoft Graph / their own token-claims path
    and pass it in).
    """
    if not subscription_id or not subscription_id.strip():
        raise ValueError("resolve_azure_workload_identity requires an explicit subscription_id.")

    if credential is None:
        try:
            from azure.identity import DefaultAzureCredential
        except ImportError as exc:
            raise WorkloadIdentityDependencyMissing(
                "'azure-identity' is not installed; cannot resolve Azure workload identity."
            ) from exc
        credential = DefaultAzureCredential()

    try:
        token = credential.get_token(scope)
    except Exception as exc:
        msg = str(exc)
        if "authenticat" in msg.lower() or "credential" in msg.lower() or "denied" in msg.lower():
            raise WorkloadIdentityDeniedError(f"Azure token acquisition denied: {msg}") from exc
        raise WorkloadIdentityUnavailableError(f"Azure token acquisition failed: {msg}") from exc

    expires_on = getattr(token, "expires_on", None)
    if expires_on is None:
        raise WorkloadIdentityUnavailableError("Azure token response did not include an expiry; cannot trust it.")
    expires_at = datetime.fromtimestamp(expires_on, tz=timezone.utc).isoformat()

    return CloudIdentityContext(
        provider=CloudAuthProvider.AZURE,
        principal_id=principal_id or "unresolved-principal",
        account_boundary=subscription_id,
        expires_at=expires_at,
        # Round-5 hostile-review fix: the previous pass resolved a real Azure token but
        # never carried the token string itself anywhere -- making it structurally
        # impossible for any caller to actually use the resolved identity. Carried here
        # exactly like AWS's temporary credentials: ephemeral, in-memory-only, never
        # logged/serialized.
        raw_claims={"bearer_token": token.token},
    )
