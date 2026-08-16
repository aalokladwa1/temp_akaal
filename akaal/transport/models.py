"""
Akaal — Generalized Transport Runtime Models (P4.7)
===================================================
Canonical dataclasses, enums, and diagnostic representations for P4.7 enterprise transport paths.
Enforces secret redaction, durable path identity, and secret-safe serialization.
"""

from enum import Enum
from typing import Dict, Any, Optional, List
import datetime
import uuid
import re


def redact_text(text: str, extra_secrets: Optional[List[str]] = None) -> str:
    """Redacts passwords, tokens, private keys, and secret values from strings/logs."""
    if not text:
        return ""
    res = str(text)
    secrets = list(extra_secrets or [])
    for s in secrets:
        if s and len(str(s)) > 2:
            res = res.replace(str(s), "[REDACTED]")
    # Pattern redactions for SSH keys, tokens, and passwords in URIs/connection strings
    res = re.sub(r'(?i)(password|secret|key|token|passphrase)=[^&\s;]+', r'\1=[REDACTED]', res)
    res = re.sub(r'-----BEGIN [A-Z ]+ PRIVATE KEY-----[\s\S]*?-----END [A-Z ]+ PRIVATE KEY-----', '[REDACTED_PRIVATE_KEY]', res)
    return res


class TransportMethod(str, Enum):
    DIRECT = "DIRECT"
    SSH_TUNNEL = "SSH_TUNNEL"
    BASTION = "BASTION"
    MULTI_HOP_SSH = "MULTI_HOP_SSH"
    HTTP_CONNECT_PROXY = "HTTP_CONNECT_PROXY"
    SOCKS5_PROXY = "SOCKS5_PROXY"
    VPN_ROUTED = "VPN_ROUTED"
    PRIVATE_ENDPOINT = "PRIVATE_ENDPOINT"
    REMOTE_AGENT = "REMOTE_AGENT"


class TransportState(str, Enum):
    UNRESOLVED = "UNRESOLVED"
    RESOLVING = "RESOLVING"
    ROUTE_READY = "ROUTE_READY"
    CONNECTING = "CONNECTING"
    AUTHENTICATING = "AUTHENTICATING"
    ESTABLISHED = "ESTABLISHED"
    DEGRADED = "DEGRADED"
    RECONNECTING = "RECONNECTING"
    FAILED = "FAILED"
    CLOSING = "CLOSING"
    CLOSED = "CLOSED"


class TransportFailureClass(str, Enum):
    NONE = "NONE"
    DNS_RESOLUTION_FAILED = "DNS_RESOLUTION_FAILED"
    DNS_IDENTITY_CHANGED = "DNS_IDENTITY_CHANGED"
    ROUTE_UNAVAILABLE = "ROUTE_UNAVAILABLE"
    CONNECT_TIMEOUT = "CONNECT_TIMEOUT"
    CONNECTION_REFUSED = "CONNECTION_REFUSED"
    CONNECTION_RESET = "CONNECTION_RESET"
    HALF_OPEN_DETECTED = "HALF_OPEN_DETECTED"
    SSH_AUTH_FAILED = "SSH_AUTH_FAILED"
    SSH_HOST_KEY_MISMATCH = "SSH_HOST_KEY_MISMATCH"
    BASTION_UNAVAILABLE = "BASTION_UNAVAILABLE"
    PROXY_AUTH_FAILED = "PROXY_AUTH_FAILED"
    PROXY_ROUTE_REJECTED = "PROXY_ROUTE_REJECTED"
    TLS_HANDSHAKE_FAILED = "TLS_HANDSHAKE_FAILED"
    TLS_IDENTITY_FAILED = "TLS_IDENTITY_FAILED"
    CREDENTIAL_EXPIRED = "CREDENTIAL_EXPIRED"
    REMOTE_AGENT_UNAVAILABLE = "REMOTE_AGENT_UNAVAILABLE"
    NETWORK_PATH_CHANGED = "NETWORK_PATH_CHANGED"
    NETWORK_PARTITION = "NETWORK_PARTITION"
    UNAUTHORIZED_SECURITY_DOWNGRADE = "UNAUTHORIZED_SECURITY_DOWNGRADE"
    LOOP_DETECTED = "LOOP_DETECTED"
    RESOURCE_EXHAUSTED = "RESOURCE_EXHAUSTED"
    UNKNOWN_NETWORK_FAILURE = "UNKNOWN_NETWORK_FAILURE"


class TransportEndpoint:
    def __init__(
        self,
        hostname: str,
        port: int,
        protocol: str = "tcp",
        service_name: Optional[str] = None,
        durable_resource_id: Optional[str] = None,
    ) -> None:
        self.hostname = hostname
        self.port = int(port)
        self.protocol = protocol.lower()
        self.service_name = service_name
        self.durable_resource_id = durable_resource_id or f"{hostname}:{port}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "hostname": self.hostname,
            "port": self.port,
            "protocol": self.protocol,
            "service_name": self.service_name,
            "durable_resource_id": self.durable_resource_id,
        }

    def __repr__(self) -> str:
        return f"TransportEndpoint({self.hostname}:{self.port}, resource={self.durable_resource_id})"


class TransportHop:
    def __init__(
        self,
        hop_id: Optional[str] = None,
        hop_type: str = "BASTION",  # BASTION, PROXY, AGENT, GATEWAY
        hostname: str = "localhost",
        port: int = 22,
        username: Optional[str] = None,
        auth_method: str = "PASSWORD",  # PASSWORD, PRIVATE_KEY, AGENT, CERTIFICATE
        credentials_ref: str = "",
        raw_credentials: Optional[Dict[str, Any]] = None,
        known_hosts_ref: Optional[str] = None,
        expected_fingerprint: Optional[str] = None,
    ) -> None:
        self.hop_id = hop_id or f"hop-{uuid.uuid4().hex[:8]}"
        self.hop_type = hop_type.upper()
        self.hostname = hostname
        self.port = int(port)
        self.username = username
        self.auth_method = auth_method.upper()
        self.credentials_ref = credentials_ref
        self._raw_credentials = dict(raw_credentials or {})
        self.known_hosts_ref = known_hosts_ref
        self.expected_fingerprint = expected_fingerprint

    def get_secret(self, key: str = "password") -> Optional[str]:
        return self._raw_credentials.get(key)

    def set_secret(self, key: str, value: str) -> None:
        self._raw_credentials[key] = value

    def to_sanitized_dict(self) -> Dict[str, Any]:
        return {
            "hop_id": self.hop_id,
            "hop_type": self.hop_type,
            "hostname": self.hostname,
            "port": self.port,
            "username": self.username,
            "auth_method": self.auth_method,
            "credentials_ref": self.credentials_ref,
            "known_hosts_ref": self.known_hosts_ref,
            "expected_fingerprint": self.expected_fingerprint,
        }

    def __repr__(self) -> str:
        return f"TransportHop(id={self.hop_id}, type={self.hop_type}, endpoint={self.hostname}:{self.port})"


class TransportPath:
    def __init__(
        self,
        path_id: Optional[str] = None,
        transport_method: TransportMethod = TransportMethod.DIRECT,
        target_endpoint: Optional[TransportEndpoint] = None,
        hops: Optional[List[TransportHop]] = None,
        network_id: Optional[str] = None,
        subnet_id: Optional[str] = None,
        security_group_ids: Optional[List[str]] = None,
        private_dns_required: bool = False,
        allow_insecure_downgrade: bool = False,
        connect_timeout_seconds: float = 10.0,
        max_hop_limit: int = 5,
    ) -> None:
        self.path_id = path_id or f"path-{uuid.uuid4().hex[:8]}"
        self.transport_method = TransportMethod(transport_method)
        self.target_endpoint = target_endpoint or TransportEndpoint("localhost", 5432)
        self.hops = list(hops or [])
        self.network_id = network_id
        self.subnet_id = subnet_id
        self.security_group_ids = list(security_group_ids or [])
        self.private_dns_required = private_dns_required
        self.allow_insecure_downgrade = allow_insecure_downgrade
        self.connect_timeout_seconds = float(connect_timeout_seconds)
        self.max_hop_limit = int(max_hop_limit)

        # Loop validation during initialization
        self.validate_path_topology()

    def validate_path_topology(self) -> None:
        """Fails closed if path length exceeds limit or contains cyclic hop references."""
        if len(self.hops) > self.max_hop_limit:
            raise ValueError(f"TransportPath hop count ({len(self.hops)}) exceeds maximum allowed limit ({self.max_hop_limit}).")

        seen_hosts = set()
        for hop in self.hops:
            key = f"{hop.hostname}:{hop.port}"
            if key in seen_hosts:
                raise ValueError(f"Loop detected in TransportPath hop chain: {key} referenced multiple times.")
            seen_hosts.add(key)

        target_key = f"{self.target_endpoint.hostname}:{self.target_endpoint.port}"
        if target_key in seen_hosts and len(self.hops) > 1:
            raise ValueError(f"Loop detected: target endpoint {target_key} is also configured as an intermediate hop.")

    def get_path_fingerprint(self) -> str:
        """Generates privacy-conscious route fingerprint to detect path mutations."""
        hop_str = "->".join(f"{h.hop_type}:{h.hostname}:{h.port}" for h in self.hops)
        return f"{self.transport_method.value}|{hop_str}|{self.target_endpoint.durable_resource_id}"

    def to_sanitized_dict(self) -> Dict[str, Any]:
        return {
            "path_id": self.path_id,
            "transport_method": self.transport_method.value,
            "target_endpoint": self.target_endpoint.to_dict(),
            "hops": [h.to_sanitized_dict() for h in self.hops],
            "network_id": self.network_id,
            "subnet_id": self.subnet_id,
            "security_group_ids": self.security_group_ids,
            "private_dns_required": self.private_dns_required,
            "allow_insecure_downgrade": self.allow_insecure_downgrade,
            "connect_timeout_seconds": self.connect_timeout_seconds,
            "path_fingerprint": self.get_path_fingerprint(),
        }


class TransportSession:
    def __init__(
        self,
        session_id: Optional[str] = None,
        job_id: str = "default-job",
        path: Optional[TransportPath] = None,
        bound_local_host: str = "127.0.0.1",
        bound_local_port: int = 0,
        socket_handle: Any = None,
        state: TransportState = TransportState.UNRESOLVED,
        failure_class: TransportFailureClass = TransportFailureClass.NONE,
        lease_duration_seconds: int = 300,
    ) -> None:
        self.session_id = session_id or f"sess-{uuid.uuid4().hex[:8]}"
        self.job_id = job_id
        self.path = path or TransportPath()
        self.bound_local_host = bound_local_host
        self.bound_local_port = bound_local_port
        self.socket_handle = socket_handle
        self.state = TransportState(state)
        self.failure_class = TransportFailureClass(failure_class)
        self.created_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
        self.lease_expires_at = (
            datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=lease_duration_seconds)
        ).isoformat()
        self.last_health_check_at = self.created_at
        self.active_ref_count = 1

    def is_lease_valid(self) -> bool:
        now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
        return self.lease_expires_at > now_str

    def to_sanitized_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "job_id": self.job_id,
            "path": self.path.to_sanitized_dict(),
            "bound_local_host": self.bound_local_host,
            "bound_local_port": self.bound_local_port,
            "state": self.state.value,
            "failure_class": self.failure_class.value,
            "created_at": self.created_at,
            "lease_expires_at": self.lease_expires_at,
            "last_health_check_at": self.last_health_check_at,
            "active_ref_count": self.active_ref_count,
        }


class TransportDiagnostics:
    def __init__(
        self,
        diagnostic_id: Optional[str] = None,
        session_id: Optional[str] = None,
        path_id: Optional[str] = None,
        status: str = "UNKNOWN",  # CONFIRMED, HIGH_CONFIDENCE, PROBABLE, UNKNOWN
        primary_failure_class: TransportFailureClass = TransportFailureClass.NONE,
        failing_hop_id: Optional[str] = None,
        latency_ms: float = 0.0,
        dns_resolution_time_ms: float = 0.0,
        tcp_handshake_time_ms: float = 0.0,
        tls_handshake_time_ms: float = 0.0,
        detailed_message: str = "",
        operator_action_hint: str = "",
    ) -> None:
        self.diagnostic_id = diagnostic_id or f"diag-{uuid.uuid4().hex[:8]}"
        self.session_id = session_id
        self.path_id = path_id
        self.status = status.upper()
        self.primary_failure_class = TransportFailureClass(primary_failure_class)
        self.failing_hop_id = failing_hop_id
        self.latency_ms = float(latency_ms)
        self.dns_resolution_time_ms = float(dns_resolution_time_ms)
        self.tcp_handshake_time_ms = float(tcp_handshake_time_ms)
        self.tls_handshake_time_ms = float(tls_handshake_time_ms)
        self.detailed_message = redact_text(detailed_message)
        self.operator_action_hint = operator_action_hint
        self.timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()

    def to_sanitized_dict(self) -> Dict[str, Any]:
        return {
            "diagnostic_id": self.diagnostic_id,
            "session_id": self.session_id,
            "path_id": self.path_id,
            "status": self.status,
            "primary_failure_class": self.primary_failure_class.value,
            "failing_hop_id": self.failing_hop_id,
            "latency_ms": self.latency_ms,
            "dns_resolution_time_ms": self.dns_resolution_time_ms,
            "tcp_handshake_time_ms": self.tcp_handshake_time_ms,
            "tls_handshake_time_ms": self.tls_handshake_time_ms,
            "detailed_message": self.detailed_message,
            "operator_action_hint": self.operator_action_hint,
            "timestamp": self.timestamp,
        }
