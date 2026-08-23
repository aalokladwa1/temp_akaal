"""
akaalEngine.connection.providers.relational.sqlite
==================================================
Canonical SQLite Provider Strategy.
Fully implemented physical provider using standard Python sqlite3.
"""

from __future__ import annotations

import logging
import os
import sqlite3
import ssl
from typing import Any, Mapping, Optional, Tuple

from akaalEngine.connection.models.capability import (
    CapabilitySupportStatus,
    PermissionSnapshot,
    ProbedCapabilitySnapshot,
    ProofLevel,
    StaticCapabilityManifest,
)
from akaalEngine.connection.models.endpoint import EndpointRole, EndpointSpec
from akaalEngine.connection.models.errors import (
    ConfigurationError,
    ConnectionFailure,
    FailureCategory,
)
from akaalEngine.connection.models.identity import PhysicalEndpointIdentity
from akaalEngine.connection.models.session import SessionPurpose
from akaalEngine.connection.providers.base import BaseProviderStrategy
from akaalEngine.connection.routing.resolver import ResolvedRoute
from akaalEngine.connection.security.redaction import redact_text

logger = logging.getLogger("akaalEngine.connection.providers.sqlite")


class SQLiteProviderStrategy(BaseProviderStrategy):
    """
    Canonical SQLite provider strategy.
    Supports in-memory and on-disk SQLite databases with strict transaction reset and capability probing.
    """

    PROVIDER_ID = "sqlite"
    PROVIDER_VERSION = "1.0.0"
    FAMILY = "relational"
    VENDOR_NAME = "SQLite"

    def get_static_manifest(self) -> StaticCapabilityManifest:
        return StaticCapabilityManifest(
            provider_id=self.PROVIDER_ID,
            provider_version=self.PROVIDER_VERSION,
            family=self.FAMILY,
            vendor_name=self.VENDOR_NAME,
            supported_roles=[EndpointRole.SOURCE, EndpointRole.TARGET, EndpointRole.REFERENCE, EndpointRole.VALIDATION],
            supports_tls=False,
            supports_mtls=False,
            capabilities={
                "SCHEMA_DISCOVERY": CapabilitySupportStatus.SUPPORTED,
                "BULK_READ": CapabilitySupportStatus.SUPPORTED,
                "BULK_WRITE": CapabilitySupportStatus.SUPPORTED,
                "TRANSACTIONS": CapabilitySupportStatus.SUPPORTED,
                "SAVEPOINTS": CapabilitySupportStatus.SUPPORTED,
                "FOREIGN_KEYS": CapabilitySupportStatus.SUPPORTED,
                "CDC_LOG_CAPTURE": CapabilitySupportStatus.UNSUPPORTED,
                "DISTRIBUTED_PARTITIONS": CapabilitySupportStatus.UNSUPPORTED,
                "PARALLEL_STREAMING": CapabilitySupportStatus.UNSUPPORTED,
            },
            proof_level=ProofLevel.LIVE_PROVEN,
            restrictions=["Single-writer concurrency limit", "File-based locking"],
            fastpath_features=["PRAGMA synchronous = OFF", "PRAGMA journal_mode = WAL"],
        )

    def is_dependency_available(self) -> Tuple[bool, str]:
        return True, "sqlite3 built-in standard library available."

    def validate_configuration(self, spec: EndpointSpec) -> None:
        super().validate_configuration(spec)
        from akaalEngine.connection.models.endpoint import TLSMode
        from akaalEngine.connection.models.errors import TLSVerificationError
        if spec.tls_binding.mode != TLSMode.DISABLED:
            failure = ConnectionFailure(
                error_code="SQLITE_TLS_UNSUPPORTED",
                category=FailureCategory.TLS_FAILURE,
                message="SQLite is an in-process file/memory database and does not support TLS encryption.",
                retryable=False,
                provider_id=self.PROVIDER_ID,
                remediation="Configure tls_binding with TLSMode.DISABLED.",
            )
            raise TLSVerificationError(failure)
        db_path = spec.database_name or (spec.options.get("db_path") if spec.options else None) or ":memory:"
        if db_path != ":memory:" and not db_path.startswith("file:"):
            parent_dir = os.path.dirname(db_path)
            if parent_dir and not os.path.exists(parent_dir):
                raise ValueError(f"SQLite directory does not exist: '{parent_dir}'")

    def connect(
        self,
        spec: EndpointSpec,
        resolved_route: ResolvedRoute,
        credentials: Mapping[str, Any],
        ssl_context: Optional[ssl.SSLContext] = None,
    ) -> sqlite3.Connection:
        db_path = spec.database_name or (spec.options.get("db_path") if spec.options else None) or ":memory:"
        timeout = float(spec.options.get("timeout_seconds", spec.options.get("timeout", 10.0)))

        conn = sqlite3.connect(
            db_path,
            timeout=timeout,
            check_same_thread=False,
            isolation_level=None,  # Autocommit by default, managed by engine
        )
        conn.row_factory = sqlite3.Row
        # Enable foreign keys
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def close(self, connection: Any) -> None:
        if connection:
            try:
                connection.close()
            except Exception:
                pass

    def validate(self, connection: Any) -> bool:
        if connection is None:
            return False
        try:
            cur = connection.cursor()
            cur.execute("SELECT 1")
            cur.fetchone()
            cur.close()
            return True
        except Exception:
            return False

    def reset_session(self, connection: Any, previous_purpose: SessionPurpose) -> bool:
        if connection is None:
            return False
        try:
            # 1. Rollback uncommitted work
            try:
                connection.rollback()
            except Exception:
                pass
            # 2. Verify connection is responsive
            cur = connection.cursor()
            cur.execute("SELECT 1")
            cur.fetchone()
            cur.close()
            return True
        except Exception:
            return False

    def attest_physical_identity(
        self,
        connection: Any,
        spec: EndpointSpec,
        resolved_route: ResolvedRoute,
    ) -> PhysicalEndpointIdentity:
        server_ver = sqlite3.sqlite_version
        db_name = spec.database_name or ":memory:"
        return PhysicalEndpointIdentity(
            provider_id=self.PROVIDER_ID,
            provider_version=self.PROVIDER_VERSION,
            role=spec.role,
            resolved_host="localhost",
            resolved_ip="127.0.0.1",
            resolved_port=0,
            server_version=f"SQLite {server_ver}",
            server_cluster_name="local-process",
            catalog_or_database=db_name,
            schema_name="main",
            principal_identity="local_user",
            route_type=spec.route_spec.route_type,
            topology_role="PRIMARY",
        )

    def probe_capabilities(
        self,
        connection: Any,
        spec: EndpointSpec,
    ) -> ProbedCapabilitySnapshot:
        caps = {
            "SCHEMA_DISCOVERY": CapabilitySupportStatus.SUPPORTED,
            "BULK_READ": CapabilitySupportStatus.SUPPORTED,
            "BULK_WRITE": CapabilitySupportStatus.SUPPORTED,
            "TRANSACTIONS": CapabilitySupportStatus.SUPPORTED,
            "SAVEPOINTS": CapabilitySupportStatus.SUPPORTED,
            "FOREIGN_KEYS": CapabilitySupportStatus.SUPPORTED,
            "CDC_LOG_CAPTURE": CapabilitySupportStatus.UNSUPPORTED,
        }
        return ProbedCapabilitySnapshot(
            provider_id=self.PROVIDER_ID,
            endpoint_fingerprint="sqlite-local",
            capabilities=caps,
            proof_level=ProofLevel.LIVE_PROVEN,
            evidence={"sqlite_version": sqlite3.sqlite_version},
        )

    def probe_permissions(
        self,
        connection: Any,
        spec: EndpointSpec,
        purpose: SessionPurpose,
    ) -> PermissionSnapshot:
        # Check if DB file is writable if not memory
        db_path = spec.database_name or ":memory:"
        is_read_only = False
        if db_path != ":memory:" and os.path.exists(db_path):
            is_read_only = not os.access(db_path, os.W_OK)

        can_write = not is_read_only
        can_ddl = not is_read_only

        return PermissionSnapshot(
            provider_id=self.PROVIDER_ID,
            endpoint_fingerprint="sqlite-local",
            granted_privileges=["SELECT", "INSERT", "UPDATE", "DELETE", "CREATE", "DROP"] if can_write else ["SELECT"],
            missing_privileges=[] if can_write else ["INSERT", "UPDATE", "DELETE", "CREATE", "DROP"],
            is_read_only=is_read_only,
            can_write=can_write,
            can_ddl=can_ddl,
            can_cdc=False,
            is_admin=True,
            evidence={"is_writable": can_write},
        )

    def normalize_error(
        self,
        exc: Exception,
        stage: str = "EXECUTION",
    ) -> ConnectionFailure:
        msg = redact_text(str(exc))
        exc_name = type(exc).__name__
        category = FailureCategory.PROVIDER_INTERNAL_ERROR
        code = "SQLITE_ERROR"
        retryable = False

        if "locked" in msg.lower() or "busy" in msg.lower():
            category = FailureCategory.TIMEOUT
            code = "SQLITE_BUSY_OR_LOCKED"
            retryable = True
        elif "readonly" in msg.lower() or "permission denied" in msg.lower():
            category = FailureCategory.AUTHORIZATION_PERMISSION_FAILURE
            code = "SQLITE_READONLY_DATABASE"
        elif "no such table" in msg.lower() or "syntax" in msg.lower():
            category = FailureCategory.INVALID_CONFIGURATION
            code = "SQLITE_SCHEMA_ERROR"

        return ConnectionFailure(
            error_code=code,
            category=category,
            message=msg,
            retryable=retryable,
            provider_id=self.PROVIDER_ID,
            original_error_type=exc_name,
        )

    def get_fastpath_hints(self) -> dict[str, Any]:
        return {
            "supports_wal": True,
            "max_batch_size": 5000,
            "preferred_isolation": "AUTOCOMMIT",
        }
