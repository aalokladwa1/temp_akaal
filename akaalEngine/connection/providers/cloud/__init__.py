"""
akaalEngine.connection.providers.cloud
======================================
Cloud managed database profile resolvers.
"""

from akaalEngine.connection.providers.cloud.aws_profiles import AWSManagedProfileResolver
from akaalEngine.connection.providers.cloud.azure_profiles import AzureManagedProfileResolver
from akaalEngine.connection.providers.cloud.gcp_profiles import GCPManagedProfileResolver
from akaalEngine.connection.providers.cloud.oci_profiles import OCIManagedProfileResolver

__all__ = [
    "AWSManagedProfileResolver",
    "AzureManagedProfileResolver",
    "GCPManagedProfileResolver",
    "OCIManagedProfileResolver",
]
