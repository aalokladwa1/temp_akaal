"""
Akaal — Managed Database & Cloud Connectivity Profiles Package (P4.6)
======================================================================
Provides canonical cloud provider discovery, managed database resource profiling,
endpoint resolution, secret-safe serialization, and canonical database adapter handoff
for AWS, Azure, GCP, and OCI managed database services.
"""

from akaal.cloud.models import CloudManagedDatabaseProfile, CloudProvider, ManagedServiceFamily, EndpointType
from akaal.cloud.resolver import resolve_cloud_profile_to_connection_config, refresh_cloud_managed_profile

__all__ = [
    "CloudManagedDatabaseProfile",
    "CloudProvider",
    "ManagedServiceFamily",
    "EndpointType",
    "resolve_cloud_profile_to_connection_config",
    "refresh_cloud_managed_profile",
]
