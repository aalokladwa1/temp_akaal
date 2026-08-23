"""
akaalEngine.connection.providers.cloud.azure_profiles
=====================================================
Azure Managed Database Profile Resolvers (Azure SQL Database, Managed Instance, Azure PostgreSQL, Azure MySQL).
"""

from __future__ import annotations

import logging
from typing import Any, Mapping, Optional

from akaalEngine.connection.models.endpoint import EndpointRole, EndpointSpec
from akaalEngine.connection.models.identity import PhysicalEndpointIdentity
from akaalEngine.connection.security.redaction import SafeReprMixin

logger = logging.getLogger("akaalEngine.connection.providers.cloud.azure")


class AzureManagedProfileResolver(SafeReprMixin):
    """
    Resolves Azure SQL / PostgreSQL / MySQL managed profiles to canonical database specs.
    """

    @classmethod
    def resolve_azure_sql_endpoint(
        cls,
        server_name: str,
        database_name: str,
        role: EndpointRole = EndpointRole.SOURCE,
        subscription_id: Optional[str] = None,
        resource_group: Optional[str] = None,
    ) -> EndpointSpec:
        host = f"{server_name}.database.windows.net" if "." not in server_name else server_name
        res_id = (
            f"/subscriptions/{subscription_id}/resourceGroups/{resource_group}/providers/Microsoft.Sql/servers/{server_name}/databases/{database_name}"
            if subscription_id and resource_group
            else None
        )
        return EndpointSpec(
            provider_id="mssql",
            host=host,
            port=1433,
            database_name=database_name,
            role=role,
            cloud_resource_id=res_id,
            options={"azure_server_name": server_name, "driver": "ODBC Driver 17 for SQL Server"},
        )

    @classmethod
    def resolve_azure_postgres_endpoint(
        cls,
        server_name: str,
        database_name: str,
        role: EndpointRole = EndpointRole.SOURCE,
    ) -> EndpointSpec:
        host = f"{server_name}.postgres.database.azure.com" if "." not in server_name else server_name
        return EndpointSpec(
            provider_id="postgresql",
            host=host,
            port=5432,
            database_name=database_name,
            role=role,
            options={"azure_server_name": server_name},
        )
