"""
akaalEngine.connection.models.session
=====================================
Canonical session models, purpose classification, isolation levels, and lease tokens.
Enforces purpose-driven read/write and DDL boundaries.
"""

from __future__ import annotations

import uuid
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping, Optional, Sequence

from akaalEngine.connection.models.endpoint import EndpointSpec
from akaalEngine.connection.security.redaction import SafeReprMixin


class SessionPurpose(str, Enum):
    """
    Strictly classified operational purpose for an endpoint session.
    Controls initialization, read/write restrictions, isolation, timeout, and pool budgeting.
    """
    DISCOVERY = "DISCOVERY"
    METADATA = "METADATA"
    SCHEMA_READ = "SCHEMA_READ"
    SCHEMA_DDL = "SCHEMA_DDL"
    BULK_SOURCE_READ = "BULK_SOURCE_READ"
    BULK_TARGET_WRITE = "BULK_TARGET_WRITE"
    CDC_CAPTURE = "CDC_CAPTURE"
    CDC_APPLY = "CDC_APPLY"
    INCREMENTAL_POLLING = "INCREMENTAL_POLLING"
    VALIDATION_READ = "VALIDATION_READ"
    RECONCILIATION_REPAIR = "RECONCILIATION_REPAIR"
    HEALTH_PROBE = "HEALTH_PROBE"
    PERMISSION_PROBE = "PERMISSION_PROBE"

    @property
    def is_read_only_by_default(self) -> bool:
        return self in (
            SessionPurpose.DISCOVERY,
            SessionPurpose.METADATA,
            SessionPurpose.SCHEMA_READ,
            SessionPurpose.BULK_SOURCE_READ,
            SessionPurpose.INCREMENTAL_POLLING,
            SessionPurpose.VALIDATION_READ,
            SessionPurpose.HEALTH_PROBE,
            SessionPurpose.PERMISSION_PROBE,
        )

    @property
    def requires_ddl_privilege(self) -> bool:
        return self == SessionPurpose.SCHEMA_DDL

    @property
    def is_long_lived(self) -> bool:
        return self in (SessionPurpose.CDC_CAPTURE, SessionPurpose.CDC_APPLY)


class IsolationLevel(str, Enum):
    """Transaction isolation levels."""
    DEFAULT = "DEFAULT"
    AUTOCOMMIT = "AUTOCOMMIT"
    READ_UNCOMMITTED = "READ_UNCOMMITTED"
    READ_COMMITTED = "READ_COMMITTED"
    REPEATABLE_READ = "REPEATABLE_READ"
    SERIALIZABLE = "SERIALIZABLE"
    SNAPSHOT = "SNAPSHOT"


@dataclass(frozen=True)
class SessionRequest(SafeReprMixin):
    """
    Request descriptor to acquire an endpoint session lease.
    """
    purpose: SessionPurpose
    endpoint_spec: EndpointSpec
    isolation_level: IsolationLevel = IsolationLevel.DEFAULT
    read_only: Optional[bool] = None            # If None, determined by purpose.is_read_only_by_default
    statement_timeout_ms: int = 60000
    lock_timeout_ms: int = 10000
    required_capabilities: Sequence[str] = field(default_factory=list)
    required_privileges: Sequence[str] = field(default_factory=list)
    application_name: str = "akaalEngine"
    correlation_id: Optional[str] = None
    borrower_id: Optional[str] = None
    deadline_epoch_ms: Optional[int] = None

    def is_effective_read_only(self) -> bool:
        # Mandatory read-only purposes can NEVER be weakened by caller
        if self.purpose.is_read_only_by_default:
            return True
        if self.read_only is not None:
            return self.read_only
        return False

    def validate_restrictions(self) -> None:
        """Validates that caller parameters do not attempt to weaken mandatory safety semantics."""
        if self.purpose.is_read_only_by_default and self.read_only is False:
            from akaalEngine.connection.models.errors import (
                ConfigurationError,
                ConnectionFailure,
                FailureCategory,
            )
            msg = f"Cannot weaken mandatory read-only session purpose '{self.purpose.value}' with read_only=False."
            failure = ConnectionFailure(
                error_code="MANDATORY_PURPOSE_RESTRICTION_VIOLATION",
                category=FailureCategory.INVALID_CONFIGURATION,
                message=msg,
                retryable=False,
                provider_id=self.endpoint_spec.provider_id,
                remediation="Remove read_only=False or select a writable session purpose.",
            )
            raise ConfigurationError(failure)


@dataclass
class InternalSessionHandle:
    """
    Engine-internal wrapper holding the live physical connection handle, route lease, and session state.
    NEVER exposed across public EngineGateway or to UI.
    """
    session_id: str
    fingerprint: str
    purpose: SessionPurpose
    provider_id: str
    physical_connection: Any
    created_at_epoch: float = field(default_factory=time.time)
    last_validated_epoch: float = field(default_factory=time.time)
    last_used_epoch: float = field(default_factory=time.time)
    in_transaction: bool = False
    is_poisoned: bool = False
    is_closed: bool = False
    session_variables: dict[str, Any] = field(default_factory=dict)
    owner_lease_id: Optional[str] = None
    process_id: int = 0
    thread_id: int = 0
    route_resource: Optional[Any] = None

    def close_route(self) -> None:
        """Closes associated route resources (e.g. SSH / Proxy tunnel lease) if attached."""
        if self.route_resource is not None:
            try:
                if hasattr(self.route_resource, "close"):
                    self.route_resource.close()
            except Exception:
                pass
            self.route_resource = None


@dataclass(frozen=True)
class SessionLease(SafeReprMixin):
    """
    Immutable borrower lease token returned to authorized Engine callers.
    Provides scoped access to an acquired physical connection session.
    """
    lease_id: str
    session_id: str
    purpose: SessionPurpose
    endpoint_fingerprint: str
    provider_id: str
    isolation_level: IsolationLevel
    is_read_only: bool
    borrower_id: str
    created_at: str
    expires_at_epoch: Optional[float] = None
    _internal_handle: Optional[InternalSessionHandle] = field(default=None, repr=False, compare=False)

    @classmethod
    def create(
        cls,
        session_handle: InternalSessionHandle,
        purpose: SessionPurpose,
        isolation_level: IsolationLevel,
        is_read_only: bool,
        borrower_id: str,
        ttl_seconds: Optional[float] = 300.0,
    ) -> SessionLease:
        lease_id = f"lease-{uuid.uuid4().hex[:12]}"
        session_handle.owner_lease_id = lease_id
        now = datetime.now(timezone.utc).isoformat()
        expires_at = (time.time() + ttl_seconds) if ttl_seconds else None
        return cls(
            lease_id=lease_id,
            session_id=session_handle.session_id,
            purpose=purpose,
            endpoint_fingerprint=session_handle.fingerprint,
            provider_id=session_handle.provider_id,
            isolation_level=isolation_level,
            is_read_only=is_read_only,
            borrower_id=borrower_id,
            created_at=now,
            expires_at_epoch=expires_at,
            _internal_handle=session_handle,
        )

    def get_physical_handle(self) -> Any:
        """
        Internal Engine accessor to retrieve the native connection handle.
        Raises RuntimeError if lease is expired or closed.
        """
        if self._internal_handle is None or self._internal_handle.is_closed:
            raise RuntimeError(f"Session lease '{self.lease_id}' is closed or invalid.")
        if self._internal_handle.is_poisoned:
            raise RuntimeError(f"Session lease '{self.lease_id}' is poisoned.")
        if self.expires_at_epoch and time.time() > self.expires_at_epoch:
            raise RuntimeError(f"Session lease '{self.lease_id}' has expired.")
        return self._internal_handle.physical_connection

    def is_valid(self) -> bool:
        if self._internal_handle is None or self._internal_handle.is_closed or self._internal_handle.is_poisoned:
            return False
        if self.expires_at_epoch and time.time() > self.expires_at_epoch:
            return False
        return True

    def sanitized_summary(self) -> dict[str, Any]:
        """Sanitized representation safe for telemetry and public Engine reports."""
        return {
            "lease_id": self.lease_id,
            "session_id": self.session_id,
            "purpose": self.purpose.value,
            "endpoint_fingerprint": self.endpoint_fingerprint,
            "provider_id": self.provider_id,
            "isolation_level": self.isolation_level.value,
            "is_read_only": self.is_read_only,
            "borrower_id": self.borrower_id,
            "created_at": self.created_at,
            "is_valid": self.is_valid(),
        }
