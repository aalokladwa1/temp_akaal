"""
akaalEngine.connection.models.endpoint
======================================
Canonical immutable models defining execution-time endpoint specifications, roles,
authentication references, TLS bindings, and network routing configurations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Optional

from akaalEngine.connection.security.redaction import redact_mapping, redact_text, SafeReprMixin


class EndpointRole(str, Enum):
    """Execution-time operational role of an endpoint."""
    SOURCE = "SOURCE"
    TARGET = "TARGET"
    REFERENCE = "REFERENCE"
    METADATA = "METADATA"
    VALIDATION = "VALIDATION"
    CDC_LOG = "CDC_LOG"
    STAGING = "STAGING"
    CUSTOM = "CUSTOM"


class AuthenticationType(str, Enum):
    """Supported authentication strategies across all providers."""
    NONE = "NONE"
    PASSWORD = "PASSWORD"
    INTEGRATED = "INTEGRATED"                   # Trusted connection / SSPI / Windows Integrated
    CERTIFICATE_MTLS = "CERTIFICATE_MTLS"
    ORACLE_WALLET = "ORACLE_WALLET"             # Oracle Wallet / Mutual TLS
    ORACLE_PRIVILEGED = "ORACLE_PRIVILEGED"     # Oracle SYSDBA / SYSOPER
    SASL_PLAIN = "SASL_PLAIN"                   # Kafka SASL/PLAIN
    SASL_SCRAM_256 = "SASL_SCRAM_256"           # Kafka SASL/SCRAM-SHA-256
    SASL_SCRAM_512 = "SASL_SCRAM_512"           # Kafka SASL/SCRAM-SHA-512
    API_KEY = "API_KEY"                         # Elasticsearch / OpenSearch API Key
    TOKEN = "TOKEN"
    KEY_PAIR = "KEY_PAIR"
    IAM_WORKLOAD_IDENTITY = "IAM_WORKLOAD_IDENTITY"
    AWS_IAM_ROLE = "AWS_IAM_ROLE"
    AZURE_ENTRA_ID = "AZURE_ENTRA_ID"
    GCP_ADC = "GCP_ADC"
    OCI_INSTANCE_PRINCIPAL = "OCI_INSTANCE_PRINCIPAL"
    SECRET_REFERENCE = "SECRET_REFERENCE"
    CUSTOM_PROVIDER = "CUSTOM_PROVIDER"


@dataclass(frozen=True, repr=False)
class AuthenticationSpec(SafeReprMixin):
    """
    Immutable authentication specification.
    Guarantees secrets are referenced by locator/ID rather than carried in plaintext.
    Supports all database, cloud, warehouse, NoSQL, and streaming secret reference types.
    """
    auth_type: AuthenticationType
    username: Optional[str] = None
    secret_ref: Optional[str] = None                   # Pointer/ID to ephemeral secret vault/store
    password_ref: Optional[str] = None                 # Explicit pointer to database password secret
    key_path: Optional[str] = None                     # Path to public/private key or cert
    role_arn: Optional[str] = None                     # Cloud IAM Role ARN or principal identifier
    token_ref: Optional[str] = None                    # Pointer to OAuth/Bearer token
    access_token_ref: Optional[str] = None             # Pointer to Personal Access Token (Databricks)
    session_token_ref: Optional[str] = None            # Pointer to STS/temporary session token
    access_key_id_ref: Optional[str] = None            # Pointer to AWS/Storage Access Key ID secret
    secret_access_key_ref: Optional[str] = None        # Pointer to AWS/Storage Secret Access Key secret
    account_key_ref: Optional[str] = None              # Pointer to Azure Storage Account Key secret
    sas_token_ref: Optional[str] = None                # Pointer to Azure SAS Token secret
    shared_access_key_ref: Optional[str] = None        # Pointer to Event Hubs SAS key secret
    service_account_json_ref: Optional[str] = None     # Pointer to GCP Service Account JSON
    connection_string_ref: Optional[str] = None        # Pointer to Azure / Provider connection string
    wallet_password_ref: Optional[str] = None          # Pointer to Oracle Wallet password
    api_key_ref: Optional[str] = None                  # Pointer to API Key secret
    secret_version: Optional[str] = "1"                # Version string for rotation detection
    additional_params: Mapping[str, Any] = field(default_factory=dict)

    def sanitized_dict(self) -> dict[str, Any]:
        return {
            "auth_type": self.auth_type.value,
            "username": self.username,
            "secret_ref": self.secret_ref,
            "password_ref": self.password_ref,
            "key_path": self.key_path,
            "role_arn": self.role_arn,
            "token_ref": self.token_ref,
            "access_token_ref": self.access_token_ref,
            "session_token_ref": self.session_token_ref,
            "access_key_id_ref": self.access_key_id_ref,
            "secret_access_key_ref": self.secret_access_key_ref,
            "account_key_ref": self.account_key_ref,
            "sas_token_ref": self.sas_token_ref,
            "shared_access_key_ref": self.shared_access_key_ref,
            "service_account_json_ref": self.service_account_json_ref,
            "connection_string_ref": self.connection_string_ref,
            "wallet_password_ref": self.wallet_password_ref,
            "api_key_ref": self.api_key_ref,
            "secret_version": self.secret_version,
            "additional_params": redact_mapping(self.additional_params),
        }


class TLSMode(str, Enum):
    """Enforceable TLS encryption and verification modes."""
    DISABLED = "DISABLED"
    PREFERRED = "PREFERRED"
    REQUIRED = "REQUIRED"
    VERIFY_CA = "VERIFY_CA"
    VERIFY_FULL = "VERIFY_FULL"


@dataclass(frozen=True, repr=False)
class TLSBinding(SafeReprMixin):
    """
    Immutable TLS/mTLS binding and certificate verification parameters.
    """
    mode: TLSMode = TLSMode.VERIFY_FULL
    ca_cert_path: Optional[str] = None
    ca_cert_pem: Optional[str] = None
    client_cert_path: Optional[str] = None
    client_key_ref: Optional[str] = None       # Ephemeral secret reference for client private key
    tls_min_version: str = "TLSv1.2"
    server_name_override: Optional[str] = None
    allow_self_signed: bool = False
    expected_cert_fingerprint: Optional[str] = None

    def sanitized_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode.value,
            "ca_cert_path": self.ca_cert_path,
            "ca_cert_pem_configured": bool(self.ca_cert_pem),
            "client_cert_path": self.client_cert_path,
            "client_key_ref_configured": bool(self.client_key_ref),
            "tls_min_version": self.tls_min_version,
            "server_name_override": self.server_name_override,
            "allow_self_signed": self.allow_self_signed,
            "expected_cert_fingerprint": self.expected_cert_fingerprint,
        }


class RouteType(str, Enum):
    """Network traversal and endpoint routing types."""
    DIRECT = "DIRECT"
    DNS_HAPPY_EYEBALLS = "DNS_HAPPY_EYEBALLS"
    PRIVATE_ENDPOINT = "PRIVATE_ENDPOINT"
    HTTP_PROXY = "HTTP_PROXY"
    SOCKS5_PROXY = "SOCKS5_PROXY"
    SSH_BASTION_TUNNEL = "SSH_BASTION_TUNNEL"


@dataclass(frozen=True, repr=False)
class RouteSpec(SafeReprMixin):
    """
    Immutable specification of network path, proxies, bastions, and transport timeouts.
    """
    route_type: RouteType = RouteType.DIRECT
    proxy_host: Optional[str] = None
    proxy_port: Optional[int] = None
    proxy_auth_spec: Optional[AuthenticationSpec] = None
    ssh_host: Optional[str] = None
    ssh_port: int = 22
    ssh_user: Optional[str] = None
    ssh_auth_spec: Optional[AuthenticationSpec] = None
    ssh_known_hosts_path: Optional[str] = None
    ssh_host_key_fingerprint: Optional[str] = None
    allow_unverified_ssh: bool = False
    private_endpoint_id: Optional[str] = None
    dns_timeout_ms: int = 5000
    connect_timeout_ms: int = 15000
    socket_timeout_ms: int = 30000
    keepalive_enabled: bool = True
    keepalive_idle_seconds: int = 60
    keepalive_interval_seconds: int = 15
    keepalive_probes: int = 5

    def sanitized_dict(self) -> dict[str, Any]:
        return {
            "route_type": self.route_type.value,
            "proxy_host": self.proxy_host,
            "proxy_port": self.proxy_port,
            "proxy_auth_configured": bool(self.proxy_auth_spec),
            "ssh_host": self.ssh_host,
            "ssh_port": self.ssh_port,
            "ssh_user": self.ssh_user,
            "ssh_auth_configured": bool(self.ssh_auth_spec),
            "ssh_known_hosts_configured": bool(self.ssh_known_hosts_path),
            "ssh_host_key_fingerprint": self.ssh_host_key_fingerprint,
            "ssh_host_verification": "PERMISSIVE_UNVERIFIED" if self.allow_unverified_ssh else "STRICT",
            "private_endpoint_id": self.private_endpoint_id,
            "dns_timeout_ms": self.dns_timeout_ms,
            "connect_timeout_ms": self.connect_timeout_ms,
            "socket_timeout_ms": self.socket_timeout_ms,
            "keepalive_enabled": self.keepalive_enabled,
        }


@dataclass(frozen=True, repr=False)
class EndpointSpec(SafeReprMixin):
    """
    Canonical, immutable specification of an endpoint ready for physical connection establishment.
    Guarantees that credentials are represented as safe references, not raw passwords.
    Supports single-host and clustered multi-endpoints (Kafka, Cassandra, ScyllaDB, Elasticsearch, etc.).
    """
    provider_id: str
    host: Optional[str] = None
    port: Optional[int] = None
    endpoints: Optional[Sequence[str]] = None   # Clustered / multi-endpoint addresses (e.g. bootstrap servers)
    database_name: Optional[str] = None
    role: EndpointRole = EndpointRole.SOURCE
    schema_name: Optional[str] = None
    auth_spec: Optional[AuthenticationSpec] = None
    tls_binding: TLSBinding = field(default_factory=TLSBinding)
    route_spec: RouteSpec = field(default_factory=RouteSpec)
    options: Mapping[str, Any] = field(default_factory=dict)
    cloud_resource_id: Optional[str] = None
    region: Optional[str] = None
    account_id: Optional[str] = None
    custom_metadata: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.endpoints is not None:
            norm_endpoints = tuple(sorted(str(e).strip() for e in self.endpoints if e and str(e).strip()))
            object.__setattr__(self, "endpoints", norm_endpoints)
        if self.provider_id and self.provider_id.strip().lower() == "sqlite":
            if self.tls_binding == TLSBinding():
                object.__setattr__(self, "tls_binding", TLSBinding(mode=TLSMode.DISABLED))

    def sanitized_dict(self) -> dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "host": self.host,
            "port": self.port,
            "endpoints": tuple(self.endpoints) if self.endpoints else None,
            "database_name": self.database_name,
            "role": self.role.value,
            "schema_name": self.schema_name,
            "auth_spec": self.auth_spec.sanitized_dict() if self.auth_spec else None,
            "tls_binding": self.tls_binding.sanitized_dict(),
            "route_spec": self.route_spec.sanitized_dict(),
            "options": redact_mapping(self.options),
            "cloud_resource_id": self.cloud_resource_id,
            "region": self.region,
            "account_id": self.account_id,
            "custom_metadata": dict(self.custom_metadata),
        }
