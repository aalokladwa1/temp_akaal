"""
akaalEngine.fabric.workload_identity.aws
===========================================
P7B.3 -- AWS IAM / STS / role assumption / workload identity resolution.

Accepts an injected `sts_client` for testing without live AWS credentials; production
code should leave it unset to use ambient boto3 credential resolution (env vars,
instance/pod identity, shared config, etc).
"""

from __future__ import annotations

from typing import Optional

from akaalEngine.fabric.workload_identity.models import (
    CloudAuthProvider,
    CloudIdentityContext,
    WorkloadIdentityDeniedError,
    WorkloadIdentityDependencyMissing,
    WorkloadIdentityUnavailableError,
)


def resolve_aws_workload_identity(
    sts_client=None,
    role_arn_to_assume: Optional[str] = None,
    session_name: str = "akaal-workload",
) -> CloudIdentityContext:
    """
    Resolves an AWS workload identity via STS. If `role_arn_to_assume` is supplied,
    performs a real AssumeRole call and returns a bounded-lifetime identity (the genuine
    "workload identity" case, always carrying a real expiry). Otherwise resolves the
    ambient caller identity via GetCallerIdentity -- STS does not expose the credential's
    own expiry through this call, so `expires_at` is truthfully left unset rather than
    fabricated; callers requiring a bounded-lifetime guarantee should always pass
    `role_arn_to_assume`.
    """
    if sts_client is None:
        try:
            import boto3
        except ImportError as exc:
            raise WorkloadIdentityDependencyMissing(
                "'boto3' is not installed; cannot resolve AWS workload identity."
            ) from exc
        sts_client = boto3.client("sts")

    try:
        if role_arn_to_assume:
            resp = sts_client.assume_role(RoleArn=role_arn_to_assume, RoleSessionName=session_name)
        else:
            resp = None
    except Exception as exc:
        msg = str(exc)
        if "AccessDenied" in msg or "not authorized" in msg:
            raise WorkloadIdentityDeniedError(f"AWS AssumeRole denied for {role_arn_to_assume!r}: {msg}") from exc
        raise WorkloadIdentityUnavailableError(f"AWS AssumeRole failed for {role_arn_to_assume!r}: {msg}") from exc

    if resp is not None:
        creds = resp["Credentials"]
        expiration = creds["Expiration"]
        expires_at = expiration.isoformat() if hasattr(expiration, "isoformat") else str(expiration)
        account_id = role_arn_to_assume.split(":")[4] if role_arn_to_assume else ""
        # Round-5 hostile-review fix: the previous pass captured only AccessKeyId,
        # dropping SecretAccessKey/SessionToken -- the two fields actually required to
        # use these temporary credentials for anything. Without them, the resolved
        # identity could never be genuinely consumed by a provider connection (a real,
        # confirmed integration gap, not a hypothetical one). All three are now carried
        # in raw_claims, which -- like ResolvedSecret -- is an ephemeral, in-memory-only
        # container never logged, serialized, or persisted anywhere in this codebase.
        return CloudIdentityContext(
            provider=CloudAuthProvider.AWS,
            principal_id=resp["AssumedRoleUser"]["Arn"],
            account_boundary=account_id,
            assumed_role=role_arn_to_assume,
            expires_at=expires_at,
            raw_claims={
                "access_key_id": creds.get("AccessKeyId", ""),
                "secret_access_key": creds.get("SecretAccessKey", ""),
                "session_token": creds.get("SessionToken", ""),
            },
        )

    try:
        identity = sts_client.get_caller_identity()
    except Exception as exc:
        msg = str(exc)
        if "AccessDenied" in msg:
            raise WorkloadIdentityDeniedError(f"AWS GetCallerIdentity denied: {msg}") from exc
        raise WorkloadIdentityUnavailableError(f"AWS GetCallerIdentity failed: {msg}") from exc

    return CloudIdentityContext(
        provider=CloudAuthProvider.AWS,
        principal_id=identity["Arn"],
        account_boundary=identity["Account"],
        expires_at=None,
    )
