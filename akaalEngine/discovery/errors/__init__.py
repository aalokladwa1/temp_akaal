"""
akaalEngine.discovery.errors
============================
Error package for Authority #3 Discovery.
"""

from akaalEngine.discovery.errors.exceptions import (
    CorruptedCatalogDiscoveryError,
    DiscoveryEngineException,
    DiscoveryTimeoutError,
    EndpointUnreachableDiscoveryError,
    ObjectDisappearedDiscoveryError,
    PermissionDeniedDiscoveryError,
    SchemaMutationDuringScanError,
    UnsupportedDiscoveryFeatureError,
)

__all__ = [
    "DiscoveryEngineException",
    "PermissionDeniedDiscoveryError",
    "EndpointUnreachableDiscoveryError",
    "ObjectDisappearedDiscoveryError",
    "DiscoveryTimeoutError",
    "CorruptedCatalogDiscoveryError",
    "UnsupportedDiscoveryFeatureError",
    "SchemaMutationDuringScanError",
]
