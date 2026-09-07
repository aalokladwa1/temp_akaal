"""akaalEngine.fabric.workload_identity -- P7B.3 Workload Identity & Cloud Authentication."""

from akaalEngine.fabric.workload_identity.models import (
    CloudAuthProvider,
    CloudIdentityContext,
    WorkloadIdentityDeniedError,
    WorkloadIdentityDependencyMissing,
    WorkloadIdentityError,
    WorkloadIdentityExpiredError,
    WorkloadIdentityUnavailableError,
)
from akaalEngine.fabric.workload_identity.boundary import (
    AKAALAuthorizationCallback,
    CloudAuthenticationBoundary,
    default_cloud_authentication_boundary,
    is_cloud_identity_usable,
)
from akaalEngine.fabric.workload_identity.aws import resolve_aws_workload_identity
from akaalEngine.fabric.workload_identity.azure import resolve_azure_workload_identity
from akaalEngine.fabric.workload_identity.gcp import resolve_gcp_workload_identity
from akaalEngine.fabric.workload_identity.oci import resolve_oci_workload_identity

__all__ = [
    "CloudAuthProvider",
    "CloudIdentityContext",
    "WorkloadIdentityDeniedError",
    "WorkloadIdentityDependencyMissing",
    "WorkloadIdentityError",
    "WorkloadIdentityExpiredError",
    "WorkloadIdentityUnavailableError",
    "AKAALAuthorizationCallback",
    "CloudAuthenticationBoundary",
    "default_cloud_authentication_boundary",
    "is_cloud_identity_usable",
    "resolve_aws_workload_identity",
    "resolve_azure_workload_identity",
    "resolve_gcp_workload_identity",
    "resolve_oci_workload_identity",
]
