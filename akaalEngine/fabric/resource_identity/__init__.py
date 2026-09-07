"""akaalEngine.fabric.resource_identity -- P7B.2 Cloud Resource Identity & Discovery."""

from akaalEngine.fabric.resource_identity.models import (
    AWSResourceLocator,
    AzureResourceLocator,
    CloudResourceLocator,
    GCPResourceLocator,
    OCIResourceLocator,
    ResourceDiscoveryRecord,
    ResourceLocatorValidationError,
    ResourceProofLevel,
)
from akaalEngine.fabric.resource_identity.discovery import (
    DiscoveryDenied,
    DiscoveryDependencyMissing,
    DiscoveryOutcome,
    DiscoveryThrottled,
    DiscoveryUnavailable,
    discover_aws_resource,
    discover_azure_resource,
    discover_gcp_resource,
    discover_oci_resource,
)

__all__ = [
    "AWSResourceLocator",
    "AzureResourceLocator",
    "CloudResourceLocator",
    "GCPResourceLocator",
    "OCIResourceLocator",
    "ResourceDiscoveryRecord",
    "ResourceLocatorValidationError",
    "ResourceProofLevel",
    "DiscoveryDenied",
    "DiscoveryDependencyMissing",
    "DiscoveryOutcome",
    "DiscoveryThrottled",
    "DiscoveryUnavailable",
    "discover_aws_resource",
    "discover_azure_resource",
    "discover_gcp_resource",
    "discover_oci_resource",
]
