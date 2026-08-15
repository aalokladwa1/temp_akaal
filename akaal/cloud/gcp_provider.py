"""
Akaal — GCP Managed Database Provider (P4.6)
============================================
Physical reality provider for Google Cloud SQL and AlloyDB database resource discovery and profiling.
Uses googleapiclient / google-cloud-sql-connector when available. Fails closed safely if SDKs are missing or credentials fail.
Redacts all secrets from error messages and logs.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional
from akaal.cloud.models import CloudManagedDatabaseProfile, CloudProvider, ManagedServiceFamily, EndpointType

logger = logging.getLogger("akaal.cloud.gcp_provider")


class GCPManagedDatabaseProvider:
    """Provider for GCP Cloud SQL and AlloyDB resource discovery and profile construction."""

    def __init__(self, project_id: str = "default-project", credentials_json: Optional[str] = None) -> None:
        self.project_id = project_id
        self.credentials_json = credentials_json

    def _redact(self, text: str) -> str:
        if not text:
            return ""
        res = str(text)
        if self.credentials_json and len(str(self.credentials_json)) > 3:
            res = res.replace(str(self.credentials_json), "[REDACTED]")
        return res

    async def discover_cloud_sql_instances(self) -> List[CloudManagedDatabaseProfile]:
        """Discovers Cloud SQL instances in the project and constructs CloudManagedDatabaseProfile objects."""
        def _run():
            try:
                from googleapiclient import discovery
                from google.oauth2 import service_account
            except ImportError as exc:
                raise RuntimeError("google-api-python-client is not installed. Cloud SQL discovery requires googleapiclient.") from exc

            try:
                if self.credentials_json:
                    import json
                    info = json.loads(self.credentials_json)
                    creds = service_account.Credentials.from_service_account_info(info)
                    service = discovery.build("sqladmin", "v1beta4", credentials=creds)
                else:
                    service = discovery.build("sqladmin", "v1beta4")
                res = service.instances().list(project=self.project_id).execute()
            except Exception as exc:
                raise RuntimeError(f"GCP Cloud SQL discovery failed: {self._redact(str(exc))}") from exc

            profiles = []
            for item in res.get("items", []):
                inst_name = item.get("name", "")
                region = item.get("region", "us-central1")
                db_ver = item.get("databaseVersion", "POSTGRES_14")

                ip_addresses = item.get("ipAddresses", [])
                public_ip = next((ip["ipAddress"] for ip in ip_addresses if ip.get("type") == "PRIMARY"), "")
                private_ip = next((ip["ipAddress"] for ip in ip_addresses if ip.get("type") == "PRIVATE"), "")

                host = public_ip or private_ip or f"{self.project_id}:{region}:{inst_name}"
                conn_name = item.get("connectionName", f"{self.project_id}:{region}:{inst_name}")

                engine_family = "POSTGRESQL"
                if "MYSQL" in db_ver:
                    engine_family = "MYSQL"
                elif "SQLSERVER" in db_ver:
                    engine_family = "MSSQL"

                port = 5432 if engine_family == "POSTGRESQL" else (3306 if engine_family == "MYSQL" else 1433)

                profile = CloudManagedDatabaseProfile(
                    display_name=f"Cloud SQL {inst_name}",
                    provider=CloudProvider.GCP,
                    project_id=self.project_id,
                    region=region,
                    resource_id=conn_name,
                    resource_name=inst_name,
                    service_family=ManagedServiceFamily.CLOUD_SQL,
                    engine_family=engine_family,
                    engine_version=db_ver,
                    deployment_type="SINGLE_INSTANCE",
                    endpoint_type=EndpointType.PUBLIC_ENDPOINT if public_ip else EndpointType.PRIVATE_ENDPOINT,
                    hostname=host,
                    port=port,
                    public_endpoint=public_ip,
                    private_endpoint=private_ip,
                    auth_mode="ADC",
                    tls_required=True,
                )
                profiles.append(profile)

            return profiles

        return await asyncio.to_thread(_run)
