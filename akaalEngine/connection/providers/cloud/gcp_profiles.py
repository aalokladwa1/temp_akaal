"""
akaalEngine.connection.providers.cloud.gcp_profiles
===================================================
GCP Managed Database Profile Resolvers (Cloud SQL PostgreSQL, MySQL, SQL Server, AlloyDB).
"""

from __future__ import annotations

import logging
from typing import Any, Mapping, Optional

from akaalEngine.connection.models.endpoint import EndpointRole, EndpointSpec
from akaalEngine.connection.security.redaction import SafeReprMixin

logger = logging.getLogger("akaalEngine.connection.providers.cloud.gcp")


class GCPManagedProfileResolver(SafeReprMixin):
    """
    Resolves GCP Cloud SQL / AlloyDB managed profiles into canonical database specs.
    """

    @classmethod
    def resolve_cloud_sql_endpoint(
        cls,
        project_id: str,
        region: str,
        instance_name: str,
        engine_type: str = "postgresql",
        public_ip: Optional[str] = None,
        private_ip: Optional[str] = None,
        database_name: Optional[str] = None,
        role: EndpointRole = EndpointRole.SOURCE,
    ) -> EndpointSpec:
        conn_name = f"{project_id}:{region}:{instance_name}"
        host = private_ip or public_ip or "127.0.0.1"

        if "postgres" in engine_type.lower() or "alloy" in engine_type.lower():
            canonical_provider = "postgresql"
            port = 5432
        elif "mysql" in engine_type.lower():
            canonical_provider = "mysql"
            port = 3306
        else:
            canonical_provider = "mssql"
            port = 1433

        return EndpointSpec(
            provider_id=canonical_provider,
            host=host,
            port=port,
            database_name=database_name,
            role=role,
            cloud_resource_id=conn_name,
            region=region,
            account_id=project_id,
            options={"gcp_connection_name": conn_name, "gcp_instance": instance_name},
        )
