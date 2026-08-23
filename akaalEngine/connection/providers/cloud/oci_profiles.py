"""
akaalEngine.connection.providers.cloud.oci_profiles
===================================================
OCI Managed Database Profile Resolvers (Autonomous Database, Base DB Systems, Exadata).
"""

from __future__ import annotations

import logging
from typing import Any, Mapping, Optional

from akaalEngine.connection.models.endpoint import EndpointRole, EndpointSpec
from akaalEngine.connection.security.redaction import SafeReprMixin

logger = logging.getLogger("akaalEngine.connection.providers.cloud.oci")


class OCIManagedProfileResolver(SafeReprMixin):
    """
    Resolves Oracle Cloud Infrastructure (OCI) Database profiles into canonical Oracle specs.
    """

    @classmethod
    def resolve_autonomous_db_endpoint(
        cls,
        db_name: str,
        tns_service_name: str,
        wallet_path: str,
        ocid: Optional[str] = None,
        role: EndpointRole = EndpointRole.SOURCE,
    ) -> EndpointSpec:
        return EndpointSpec(
            provider_id="oracle",
            host="adb.oraclecloud.com",
            port=1522,
            database_name=db_name,
            role=role,
            cloud_resource_id=ocid,
            options={"service_name": tns_service_name, "wallet_location": wallet_path},
        )
