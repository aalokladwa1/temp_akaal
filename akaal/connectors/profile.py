"""
AKAAL Canonical Connection Profile & Credentials Sanitization Model (P4.1).
=============================================================================
Defines reusable connection profiles with strict credential safety:
- Plaintext secrets are NEVER persisted, logged, or serialized into telemetry/DTOs.
- Recursive sanitization for arbitrary nested configuration payloads.
- String representations (__repr__, __str__) strictly omit secrets.
"""

from typing import Dict, Any, Optional, List
import datetime
import uuid

from akaal.connectors.taxonomy import ConnectorFamily, AuthenticationMechanism

SENSITIVE_KEY_SUBSTRINGS = (
    "pass", "pwd", "secret", "token", "key", "auth", "cert",
    "private", "credential", "wallet", "api_key", "bearer", "signature",
)


def recursive_sanitize(obj: Any) -> Any:
    """Recursively redacts sensitive keys from dictionaries, lists, and primitives."""
    if isinstance(obj, dict):
        sanitized = {}
        for k, v in obj.items():
            k_lower = str(k).lower()
            if any(sub in k_lower for sub in SENSITIVE_KEY_SUBSTRINGS):
                sanitized[k] = "[REDACTED]"
            else:
                sanitized[k] = recursive_sanitize(v)
        return sanitized
    elif isinstance(obj, (list, tuple, set)):
        return [recursive_sanitize(item) for item in obj]
    return obj


class ConnectionProfile:
    """
    Canonical, reusable connection profile descriptor for source/target endpoints.
    Enforces secret sanitization: credentials_ref points to secure vault, never plaintext secrets.
    """

    def __init__(
        self,
        connection_id: Optional[str] = None,
        display_name: str = "Default Connection",
        connector_id: str = "conn-generic",
        family: ConnectorFamily = ConnectorFamily.RELATIONAL_DATABASE,
        environment: str = "PRODUCTION",
        host: str = "localhost",
        port: int = 5432,
        database_name: str = "",
        schema_name: str = "",
        region: Optional[str] = None,
        cloud_provider: Optional[str] = None,
        auth_mechanism: AuthenticationMechanism = AuthenticationMechanism.USERNAME_PASSWORD,
        credentials_ref: str = "",
        raw_credentials: Optional[Dict[str, Any]] = None,
        tls_enabled: bool = False,
        tls_ca_cert_ref: Optional[str] = None,
        tls_client_cert_ref: Optional[str] = None,
        verify_hostname: bool = True,
        ssh_tunnel_enabled: bool = False,
        ssh_bastion_host: Optional[str] = None,
        ssh_bastion_port: int = 22,
        ssh_bastion_user: Optional[str] = None,
        ssh_key_ref: Optional[str] = None,
        connection_timeout_sec: int = 30,
        read_timeout_sec: int = 60,
        pool_options: Optional[Dict[str, Any]] = None,
        driver_options: Optional[Dict[str, Any]] = None,
        health_metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.connection_id = connection_id or f"conn-{uuid.uuid4().hex[:8]}"
        self.display_name = display_name
        self.connector_id = str(connector_id).strip().lower()
        self.family = family
        self.environment = environment.upper()
        self.host = host
        self.port = port
        self.database_name = database_name
        self.schema_name = schema_name
        self.region = region
        self.cloud_provider = cloud_provider
        self.auth_mechanism = auth_mechanism
        self.credentials_ref = credentials_ref or f"vault-ref-{self.connection_id}"
        self._raw_credentials = dict(raw_credentials or {})
        self.tls_enabled = tls_enabled
        self.tls_ca_cert_ref = tls_ca_cert_ref
        self.tls_client_cert_ref = tls_client_cert_ref
        self.verify_hostname = verify_hostname
        self.ssh_tunnel_enabled = ssh_tunnel_enabled
        self.ssh_bastion_host = ssh_bastion_host
        self.ssh_bastion_port = ssh_bastion_port
        self.ssh_bastion_user = ssh_bastion_user
        self.ssh_key_ref = ssh_key_ref
        self.connection_timeout_sec = connection_timeout_sec
        self.read_timeout_sec = read_timeout_sec
        self.pool_options = dict(pool_options or {"min_size": 1, "max_size": 10, "timeout": 30})
        self.driver_options = dict(driver_options or {})
        self.health_metadata = dict(health_metadata or {})
        self.created_at = datetime.datetime.now(datetime.timezone.utc).isoformat()

    def get_effective_secret(self, key: str = "password") -> Optional[str]:
        """Retrieves raw credential in-memory during active connection establishment only."""
        return self._raw_credentials.get(key)

    def set_effective_secret(self, key: str, value: str) -> None:
        """Sets temporary in-memory credential."""
        self._raw_credentials[key] = value

    def to_sanitized_dict(self) -> Dict[str, Any]:
        """Returns completely sanitized dictionary safe for IPC, UI, Telemetry, and State Persistence."""
        return {
            "connection_id": self.connection_id,
            "display_name": self.display_name,
            "connector_id": self.connector_id,
            "family": self.family.value if hasattr(self.family, "value") else str(self.family),
            "environment": self.environment,
            "host": self.host,
            "port": self.port,
            "database_name": self.database_name,
            "schema_name": self.schema_name,
            "region": self.region,
            "cloud_provider": self.cloud_provider,
            "auth_mechanism": self.auth_mechanism.value if hasattr(self.auth_mechanism, "value") else str(self.auth_mechanism),
            "credentials_ref": self.credentials_ref,
            "tls_enabled": self.tls_enabled,
            "tls_ca_cert_ref": self.tls_ca_cert_ref,
            "tls_client_cert_ref": self.tls_client_cert_ref,
            "verify_hostname": self.verify_hostname,
            "ssh_tunnel_enabled": self.ssh_tunnel_enabled,
            "ssh_bastion_host": self.ssh_bastion_host,
            "ssh_bastion_port": self.ssh_bastion_port,
            "ssh_bastion_user": self.ssh_bastion_user,
            "connection_timeout_sec": self.connection_timeout_sec,
            "read_timeout_sec": self.read_timeout_sec,
            "pool_options": recursive_sanitize(self.pool_options),
            "driver_options": recursive_sanitize(self.driver_options),
            "health_metadata": recursive_sanitize(self.health_metadata),
            "created_at": self.created_at,
        }

    def to_dict(self) -> Dict[str, Any]:
        """Synonym for sanitized dictionary."""
        return self.to_sanitized_dict()

    def __repr__(self) -> str:
        return (
            f"ConnectionProfile(id={self.connection_id}, connector={self.connector_id}, "
            f"family={self.family.value}, host={self.host}:{self.port}, db={self.database_name}, "
            f"auth_ref={self.credentials_ref})"
        )

    def __str__(self) -> str:
        return self.__repr__()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConnectionProfile":
        family_str = data.get("family", ConnectorFamily.RELATIONAL_DATABASE.value)
        try:
            family = ConnectorFamily(family_str)
        except ValueError:
            family = ConnectorFamily.RELATIONAL_DATABASE

        auth_str = data.get("auth_mechanism", AuthenticationMechanism.USERNAME_PASSWORD.value)
        try:
            auth = AuthenticationMechanism(auth_str)
        except ValueError:
            auth = AuthenticationMechanism.USERNAME_PASSWORD

        return cls(
            connection_id=data.get("connection_id"),
            display_name=data.get("display_name", "Default Connection"),
            connector_id=data.get("connector_id", "conn-generic"),
            family=family,
            environment=data.get("environment", "PRODUCTION"),
            host=data.get("host", "localhost"),
            port=int(data.get("port", 5432)),
            database_name=data.get("database_name", ""),
            schema_name=data.get("schema_name", ""),
            region=data.get("region"),
            cloud_provider=data.get("cloud_provider"),
            auth_mechanism=auth,
            credentials_ref=data.get("credentials_ref", ""),
            raw_credentials=data.get("raw_credentials"),
            tls_enabled=data.get("tls_enabled", False),
            tls_ca_cert_ref=data.get("tls_ca_cert_ref"),
            tls_client_cert_ref=data.get("tls_client_cert_ref"),
            verify_hostname=data.get("verify_hostname", True),
            ssh_tunnel_enabled=data.get("ssh_tunnel_enabled", False),
            ssh_bastion_host=data.get("ssh_bastion_host"),
            ssh_bastion_port=int(data.get("ssh_bastion_port", 22)),
            ssh_bastion_user=data.get("ssh_bastion_user"),
            ssh_key_ref=data.get("ssh_key_ref"),
            connection_timeout_sec=int(data.get("connection_timeout_sec", 30)),
            read_timeout_sec=int(data.get("read_timeout_sec", 60)),
            pool_options=data.get("pool_options"),
            driver_options=data.get("driver_options"),
            health_metadata=data.get("health_metadata"),
        )
