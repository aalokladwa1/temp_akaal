"""
Akaal — AWS Managed Database Provider (P4.6)
============================================
Physical reality provider for AWS RDS and Amazon Aurora database resource discovery and profiling.
Uses boto3 RDS client when available. Fails closed safely if boto3 is missing or credentials fail.
Redacts all credentials from error messages and logs.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional
from akaal.cloud.models import CloudManagedDatabaseProfile, CloudProvider, ManagedServiceFamily, EndpointType
from akaal.connectors.profile import recursive_sanitize

logger = logging.getLogger("akaal.cloud.aws_provider")


class AWSManagedDatabaseProvider:
    """Provider for Amazon RDS and Amazon Aurora resource discovery and profile construction."""

    def __init__(self, region: str = "us-east-1", aws_access_key_id: Optional[str] = None, aws_secret_access_key: Optional[str] = None, aws_session_token: Optional[str] = None) -> None:
        self.region = region
        self.aws_access_key_id = aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key
        self.aws_session_token = aws_session_token

    def _redact(self, text: str) -> str:
        if not text:
            return ""
        res = str(text)
        for k in [self.aws_access_key_id, self.aws_secret_access_key, self.aws_session_token]:
            if k and len(str(k)) > 3:
                res = res.replace(str(k), "[REDACTED]")
        return res

    async def _get_rds_client(self) -> Any:
        try:
            import boto3
        except ImportError as exc:
            raise RuntimeError("boto3 is not installed. AWS managed database discovery requires boto3.") from exc

        def _connect():
            session = boto3.Session(
                aws_access_key_id=self.aws_access_key_id,
                aws_secret_access_key=self.aws_secret_access_key,
                aws_session_token=self.aws_session_token,
                region_name=self.region,
            )
            return session.client("rds")

        return await asyncio.to_thread(_connect)

    async def discover_instances(self, db_instance_identifier: Optional[str] = None) -> List[CloudManagedDatabaseProfile]:
        """Discovers RDS DB Instances and constructs CloudManagedDatabaseProfile objects."""
        client = await self._get_rds_client()

        def _run():
            kwargs = {}
            if db_instance_identifier:
                kwargs["DBInstanceIdentifier"] = db_instance_identifier

            try:
                res = client.describe_db_instances(**kwargs)
            except Exception as exc:
                raise RuntimeError(f"AWS RDS DescribeDBInstances failed: {self._redact(str(exc))}") from exc

            profiles = []
            for item in res.get("DBInstances", []):
                inst_id = item.get("DBInstanceIdentifier", "")
                engine = item.get("Engine", "").upper()
                engine_ver = item.get("EngineVersion", "")
                arn = item.get("DBInstanceArn", "")
                endpoint = item.get("Endpoint", {})
                host = endpoint.get("Address", "")
                port = endpoint.get("Port", 5432)
                db_name = item.get("DBName", "")
                is_public = item.get("PubliclyAccessible", False)
                vpc_id = item.get("DBSubnetGroup", {}).get("VpcId", "")
                sec_groups = [sg.get("VpcSecurityGroupId") for sg in item.get("VpcSecurityGroups", []) if sg.get("VpcSecurityGroupId")]

                engine_family = "POSTGRESQL"
                if "mysql" in engine:
                    engine_family = "MYSQL"
                elif "oracle" in engine:
                    engine_family = "ORACLE"
                elif "sqlserver" in engine:
                    engine_family = "MSSQL"
                elif "mariadb" in engine:
                    engine_family = "MARIADB"

                profile = CloudManagedDatabaseProfile(
                    display_name=f"RDS {inst_id}",
                    provider=CloudProvider.AWS,
                    account_id=arn.split(":")[4] if arn.count(":") >= 4 else None,
                    region=self.region,
                    resource_id=arn or inst_id,
                    resource_name=inst_id,
                    service_family=ManagedServiceFamily.RDS,
                    engine_family=engine_family,
                    engine_version=engine_ver,
                    deployment_type="MULTI_AZ" if item.get("MultiAZ") else "SINGLE_INSTANCE",
                    endpoint_type=EndpointType.PUBLIC_ENDPOINT if is_public else EndpointType.PRIVATE_ENDPOINT,
                    hostname=host,
                    port=port,
                    database_name=db_name,
                    instance_identifier=inst_id,
                    writer_endpoint=host,
                    network_id=vpc_id,
                    security_group_ids=sec_groups,
                    auth_mode="IAM_ROLE" if item.get("IAMDatabaseAuthenticationEnabled") else "PASSWORD",
                    tls_required=True,
                )
                profiles.append(profile)

            return profiles

        return await asyncio.to_thread(_run)

    async def discover_clusters(self, db_cluster_identifier: Optional[str] = None) -> List[CloudManagedDatabaseProfile]:
        """Discovers Aurora DB Clusters and constructs CloudManagedDatabaseProfile objects."""
        client = await self._get_rds_client()

        def _run():
            kwargs = {}
            if db_cluster_identifier:
                kwargs["DBClusterIdentifier"] = db_cluster_identifier

            try:
                res = client.describe_db_clusters(**kwargs)
            except Exception as exc:
                raise RuntimeError(f"AWS RDS DescribeDBClusters failed: {self._redact(str(exc))}") from exc

            profiles = []
            for item in res.get("DBClusters", []):
                cluster_id = item.get("DBClusterIdentifier", "")
                engine = item.get("Engine", "").upper()
                engine_ver = item.get("EngineVersion", "")
                arn = item.get("DBClusterArn", "")
                host = item.get("Endpoint", "")
                reader_host = item.get("ReaderEndpoint")
                port = item.get("Port", 5432)
                db_name = item.get("DatabaseName", "")

                engine_family = "POSTGRESQL" if "postgres" in engine else "MYSQL"

                profile = CloudManagedDatabaseProfile(
                    display_name=f"Aurora {cluster_id}",
                    provider=CloudProvider.AWS,
                    account_id=arn.split(":")[4] if arn.count(":") >= 4 else None,
                    region=self.region,
                    resource_id=arn or cluster_id,
                    resource_name=cluster_id,
                    service_family=ManagedServiceFamily.AURORA,
                    engine_family=engine_family,
                    engine_version=engine_ver,
                    deployment_type="CLUSTER",
                    endpoint_type=EndpointType.PRIMARY_WRITER,
                    hostname=host,
                    port=port,
                    database_name=db_name,
                    cluster_identifier=cluster_id,
                    writer_endpoint=host,
                    reader_endpoint=reader_host,
                    auth_mode="IAM_ROLE" if item.get("IAMDatabaseAuthenticationEnabled") else "PASSWORD",
                    tls_required=True,
                )
                profiles.append(profile)

            return profiles

        return await asyncio.to_thread(_run)
