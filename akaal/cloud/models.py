"""
Akaal — Cloud Managed Database Profile Models (P4.6)
====================================================
Defines canonical dataclasses and enums for AWS, Azure, GCP, and OCI managed database resources.
Enforces strict secret separation, durable resource identity, and secret-safe serialization.
"""

from enum import Enum
from typing import Dict, Any, Optional, List
import datetime
import uuid

from akaal.connectors.profile import recursive_sanitize


class CloudProvider(str, Enum):
    AWS = "AWS"
    AZURE = "AZURE"
    GCP = "GCP"
    OCI = "OCI"


class ManagedServiceFamily(str, Enum):
    # AWS
    RDS = "RDS"
    AURORA = "AURORA"
    # Azure
    AZURE_SQL = "AZURE_SQL"
    AZURE_SQL_MANAGED_INSTANCE = "AZURE_SQL_MANAGED_INSTANCE"
    AZURE_POSTGRESQL = "AZURE_POSTGRESQL"
    AZURE_MYSQL = "AZURE_MYSQL"
    # GCP
    CLOUD_SQL = "CLOUD_SQL"
    ALLOYDB = "ALLOYDB"
    # OCI
    AUTONOMOUS_DATABASE = "AUTONOMOUS_DATABASE"
    BASE_DATABASE_SERVICE = "BASE_DATABASE_SERVICE"
    EXADATA_SERVICE = "EXADATA_SERVICE"


class EndpointType(str, Enum):
    PRIMARY_WRITER = "PRIMARY_WRITER"
    READER_REPLICA = "READER_REPLICA"
    FAILOVER = "FAILOVER"
    PRIVATE_ENDPOINT = "PRIVATE_ENDPOINT"
    PUBLIC_ENDPOINT = "PUBLIC_ENDPOINT"
    UNKNOWN = "UNKNOWN"


class CloudManagedDatabaseProfile:
    """
    Canonical Cloud Managed Database Profile representation for AWS, Azure, GCP, and OCI.
    Stores durable provider resource identity, endpoint topology, network/TLS metadata, and auth mode.
    Enforces secret-safe serialization (plaintext credentials are NEVER serialized).
    """

    def __init__(
        self,
        profile_id: Optional[str] = None,
        display_name: str = "Managed Database Connection",
        provider: CloudProvider = CloudProvider.AWS,
        cloud_environment: str = "COMMERCIAL",
        account_id: Optional[str] = None,
        subscription_id: Optional[str] = None,
        project_id: Optional[str] = None,
        tenancy_id: Optional[str] = None,
        compartment_id: Optional[str] = None,
        region: str = "us-east-1",
        location: Optional[str] = None,
        resource_id: str = "",
        resource_name: str = "",
        service_family: ManagedServiceFamily = ManagedServiceFamily.RDS,
        engine_family: str = "POSTGRESQL",
        engine_version: str = "",
        deployment_type: str = "SINGLE_INSTANCE",
        endpoint_type: EndpointType = EndpointType.PRIMARY_WRITER,
        hostname: str = "localhost",
        port: int = 5432,
        database_name: str = "",
        service_name: Optional[str] = None,
        cluster_identifier: Optional[str] = None,
        instance_identifier: Optional[str] = None,
        writer_endpoint: Optional[str] = None,
        reader_endpoint: Optional[str] = None,
        failover_endpoint: Optional[str] = None,
        private_endpoint: Optional[str] = None,
        public_endpoint: Optional[str] = None,
        network_id: Optional[str] = None,  # vpc_id / vnet_id / vcn_id
        subnet_id: Optional[str] = None,
        security_group_ids: Optional[List[str]] = None,
        vnet_id: Optional[str] = None,
        vcn_id: Optional[str] = None,
        private_dns_required: bool = False,
        bastion_reference: Optional[str] = None,
        jump_host_reference: Optional[str] = None,
        auth_mode: str = "PASSWORD",
        credentials_ref: str = "",
        raw_credentials: Optional[Dict[str, Any]] = None,
        tls_required: bool = True,
        tls_ca_cert_ref: Optional[str] = None,
        verify_hostname: bool = True,
        wallet_ref: Optional[str] = None,
        discovery_timestamp: Optional[str] = None,
        endpoint_refresh_timestamp: Optional[str] = None,
        extra_metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.profile_id = profile_id or f"cmp-{uuid.uuid4().hex[:8]}"
        self.display_name = display_name
        self.provider = CloudProvider(provider)
        self.cloud_environment = cloud_environment.upper()
        self.account_id = account_id
        self.subscription_id = subscription_id
        self.project_id = project_id
        self.tenancy_id = tenancy_id
        self.compartment_id = compartment_id
        self.region = region
        self.location = location or region
        self.resource_id = resource_id or f"res-{self.profile_id}"
        self.resource_name = resource_name
        self.service_family = ManagedServiceFamily(service_family)
        self.engine_family = engine_family.upper()
        self.engine_version = engine_version
        self.deployment_type = deployment_type.upper()
        self.endpoint_type = EndpointType(endpoint_type)
        self.hostname = hostname
        self.port = port
        self.database_name = database_name
        self.service_name = service_name
        self.cluster_identifier = cluster_identifier
        self.instance_identifier = instance_identifier
        self.writer_endpoint = writer_endpoint or hostname
        self.reader_endpoint = reader_endpoint
        self.failover_endpoint = failover_endpoint
        self.private_endpoint = private_endpoint
        self.public_endpoint = public_endpoint
        self.network_id = network_id
        self.subnet_id = subnet_id
        self.security_group_ids = list(security_group_ids or [])
        self.vnet_id = vnet_id
        self.vcn_id = vcn_id
        self.private_dns_required = private_dns_required
        self.bastion_reference = bastion_reference
        self.jump_host_reference = jump_host_reference
        self.auth_mode = auth_mode.upper()
        self.credentials_ref = credentials_ref or f"vault-ref-{self.profile_id}"
        self._raw_credentials = dict(raw_credentials or {})
        self.tls_required = tls_required
        self.tls_ca_cert_ref = tls_ca_cert_ref
        self.verify_hostname = verify_hostname
        self.wallet_ref = wallet_ref
        self.discovery_timestamp = discovery_timestamp or datetime.datetime.now(datetime.timezone.utc).isoformat()
        self.endpoint_refresh_timestamp = endpoint_refresh_timestamp or self.discovery_timestamp
        self.extra_metadata = dict(extra_metadata or {})

    def get_effective_secret(self, key: str = "password") -> Optional[str]:
        return self._raw_credentials.get(key)

    def set_effective_secret(self, key: str, value: str) -> None:
        self._raw_credentials[key] = value

    def to_sanitized_dict(self) -> Dict[str, Any]:
        """Returns sanitized dictionary safe for IPC, UI, Telemetry, and State Persistence."""
        return {
            "profile_id": self.profile_id,
            "display_name": self.display_name,
            "provider": self.provider.value,
            "cloud_environment": self.cloud_environment,
            "account_id": self.account_id,
            "subscription_id": self.subscription_id,
            "project_id": self.project_id,
            "tenancy_id": self.tenancy_id,
            "compartment_id": self.compartment_id,
            "region": self.region,
            "location": self.location,
            "resource_id": self.resource_id,
            "resource_name": self.resource_name,
            "service_family": self.service_family.value,
            "engine_family": self.engine_family,
            "engine_version": self.engine_version,
            "deployment_type": self.deployment_type,
            "endpoint_type": self.endpoint_type.value,
            "hostname": self.hostname,
            "port": self.port,
            "database_name": self.database_name,
            "service_name": self.service_name,
            "cluster_identifier": self.cluster_identifier,
            "instance_identifier": self.instance_identifier,
            "writer_endpoint": self.writer_endpoint,
            "reader_endpoint": self.reader_endpoint,
            "failover_endpoint": self.failover_endpoint,
            "private_endpoint": self.private_endpoint,
            "public_endpoint": self.public_endpoint,
            "network_id": self.network_id,
            "subnet_id": self.subnet_id,
            "security_group_ids": self.security_group_ids,
            "vnet_id": self.vnet_id,
            "vcn_id": self.vcn_id,
            "private_dns_required": self.private_dns_required,
            "bastion_reference": self.bastion_reference,
            "jump_host_reference": self.jump_host_reference,
            "auth_mode": self.auth_mode,
            "credentials_ref": self.credentials_ref,
            "tls_required": self.tls_required,
            "tls_ca_cert_ref": self.tls_ca_cert_ref,
            "verify_hostname": self.verify_hostname,
            "wallet_ref": self.wallet_ref,
            "discovery_timestamp": self.discovery_timestamp,
            "endpoint_refresh_timestamp": self.endpoint_refresh_timestamp,
            "extra_metadata": recursive_sanitize(self.extra_metadata),
        }

    def to_dict(self) -> Dict[str, Any]:
        return self.to_sanitized_dict()

    def __repr__(self) -> str:
        return (
            f"CloudManagedDatabaseProfile(id={self.profile_id}, provider={self.provider.value}, "
            f"service={self.service_family.value}, resource={self.resource_id}, "
            f"endpoint={self.hostname}:{self.port}, db={self.database_name})"
        )

    def __str__(self) -> str:
        return self.__repr__()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CloudManagedDatabaseProfile":
        return cls(
            profile_id=data.get("profile_id"),
            display_name=data.get("display_name", "Managed Database Connection"),
            provider=CloudProvider(data.get("provider", "AWS")),
            cloud_environment=data.get("cloud_environment", "COMMERCIAL"),
            account_id=data.get("account_id"),
            subscription_id=data.get("subscription_id"),
            project_id=data.get("project_id"),
            tenancy_id=data.get("tenancy_id"),
            compartment_id=data.get("compartment_id"),
            region=data.get("region", "us-east-1"),
            location=data.get("location"),
            resource_id=data.get("resource_id", ""),
            resource_name=data.get("resource_name", ""),
            service_family=ManagedServiceFamily(data.get("service_family", "RDS")),
            engine_family=data.get("engine_family", "POSTGRESQL"),
            engine_version=data.get("engine_version", ""),
            deployment_type=data.get("deployment_type", "SINGLE_INSTANCE"),
            endpoint_type=EndpointType(data.get("endpoint_type", "PRIMARY_WRITER")),
            hostname=data.get("hostname", "localhost"),
            port=int(data.get("port", 5432)),
            database_name=data.get("database_name", ""),
            service_name=data.get("service_name"),
            cluster_identifier=data.get("cluster_identifier"),
            instance_identifier=data.get("instance_identifier"),
            writer_endpoint=data.get("writer_endpoint"),
            reader_endpoint=data.get("reader_endpoint"),
            failover_endpoint=data.get("failover_endpoint"),
            private_endpoint=data.get("private_endpoint"),
            public_endpoint=data.get("public_endpoint"),
            network_id=data.get("network_id"),
            subnet_id=data.get("subnet_id"),
            security_group_ids=data.get("security_group_ids"),
            vnet_id=data.get("vnet_id"),
            vcn_id=data.get("vcn_id"),
            private_dns_required=data.get("private_dns_required", False),
            bastion_reference=data.get("bastion_reference"),
            jump_host_reference=data.get("jump_host_reference"),
            auth_mode=data.get("auth_mode", "PASSWORD"),
            credentials_ref=data.get("credentials_ref", ""),
            raw_credentials=data.get("raw_credentials"),
            tls_required=data.get("tls_required", True),
            tls_ca_cert_ref=data.get("tls_ca_cert_ref"),
            verify_hostname=data.get("verify_hostname", True),
            wallet_ref=data.get("wallet_ref"),
            discovery_timestamp=data.get("discovery_timestamp"),
            endpoint_refresh_timestamp=data.get("endpoint_refresh_timestamp"),
            extra_metadata=data.get("extra_metadata"),
        )
