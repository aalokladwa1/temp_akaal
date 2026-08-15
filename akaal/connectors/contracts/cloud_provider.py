"""
AKAAL Cloud Provider & Connectivity Infrastructure Extension Contract (P4.1).
================================================================================
Defines cloud infrastructure and platform discovery capability extension interfaces:
- AWS, Azure, GCP, OCI
- Managed database endpoint discovery
- Private link / VPC endpoint metadata
- Cloud IAM & token discovery
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional


class ICloudProviderCapability(ABC):
    """Extension contract for Cloud Platform integrations (AWS, Azure, GCP, OCI)."""

    @abstractmethod
    async def discover_managed_databases(self, region: Optional[str] = None) -> List[Dict[str, Any]]:
        """Discovers managed database instances (e.g. RDS, Aurora, Cloud SQL, Azure SQL)."""
        pass

    @abstractmethod
    async def get_private_endpoint_metadata(self, resource_id: str) -> Dict[str, Any]:
        """Retrieves private connectivity and VPC endpoint metadata."""
        pass

    @abstractmethod
    async def generate_iam_auth_token(self, host: str, port: int, user: str) -> str:
        """Generates short-lived IAM authentication token for managed database."""
        pass
