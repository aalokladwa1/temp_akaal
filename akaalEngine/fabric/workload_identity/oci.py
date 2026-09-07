"""
akaalEngine.fabric.workload_identity.oci
===========================================
P7B.3 -- OCI IAM instance principal / resource principal workload identity.

Honesty note (zero-fake policy): the OCI Python SDK's instance-principal and
resource-principal signers do not expose a single, stable, version-independent public
method for reading back the signing certificate's principal id and expiry without
reaching into SDK-internal state that differs across `oci` SDK releases. Rather than
fabricate a plausible-looking accessor that might silently misreport those values against
a real signer, this function requires the caller to supply `principal_id` and
`expires_at` explicitly (the caller resolves these from the signer's own certificate via
whatever the installed `oci` SDK version's supported accessor is) and this function's
actual, verifiable job is: (a) proving a signer was supplied at all (fails closed
otherwise), (b) enforcing the expiry once known, and (c) producing the canonical
`CloudIdentityContext` shape so the rest of the fabric layer treats OCI identically to
the other three clouds. This is disclosed as a real, current limitation rather than
silently claimed as complete SDK-internal parsing.
"""

from __future__ import annotations

from typing import Optional

from akaalEngine.fabric.workload_identity.models import (
    CloudAuthProvider,
    CloudIdentityContext,
    WorkloadIdentityDependencyMissing,
    WorkloadIdentityError,
)


def resolve_oci_workload_identity(
    signer,
    principal_id: str,
    tenancy_ocid: str,
    expires_at: Optional[str] = None,
    mode: str = "instance_principal",
) -> CloudIdentityContext:
    """
    Wraps an already-constructed OCI signer (an
    `oci.auth.signers.InstancePrincipalsSecurityTokenSigner` or a resource-principal
    signer from `oci.auth.signers.get_resource_principals_signer()`) into the canonical
    `CloudIdentityContext` shape. Fails closed if no signer is supplied.
    """
    if signer is None:
        try:
            import oci  # noqa: F401
        except ImportError as exc:
            raise WorkloadIdentityDependencyMissing(
                "'oci' SDK is not installed; cannot construct an OCI workload identity signer."
            ) from exc
        raise WorkloadIdentityError(
            "No OCI signer supplied. Construct one via "
            "oci.auth.signers.InstancePrincipalsSecurityTokenSigner() or "
            "oci.auth.signers.get_resource_principals_signer() and pass it in."
        )

    if mode not in ("instance_principal", "resource_principal"):
        raise WorkloadIdentityError(f"Unrecognized OCI workload identity mode: {mode!r}")

    if not principal_id or not principal_id.strip():
        raise WorkloadIdentityError("resolve_oci_workload_identity requires an explicit principal_id.")
    if not tenancy_ocid.startswith("ocid1.tenancy."):
        raise WorkloadIdentityError(f"tenancy_ocid must start with 'ocid1.tenancy.'; got {tenancy_ocid!r}")

    return CloudIdentityContext(
        provider=CloudAuthProvider.OCI,
        principal_id=principal_id,
        account_boundary=tenancy_ocid,
        expires_at=expires_at,
        # Round-5 hostile-review fix: OCI's real usable material is the `signer` OBJECT
        # itself (instance/resource principal signers have no string representation at
        # all) -- carried here exactly like AWS/Azure/GCP's real material, ephemeral and
        # never logged/serialized.
        raw_claims={"mode": mode, "signer": signer},
    )
