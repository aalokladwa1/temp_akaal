"""
akaalIPC.protocol.schemas
============================
Explicit request/response schema registration and validation.

This module is the extensibility seam future request types register
through. It intentionally does NOT contain a big if/elif dispatch table —
registration is data (a ``SchemaDescriptor`` + a validator callable), and
the router (``application.router``) consults this registry generically for
every request regardless of which client type or downstream capability it
targets.

No business execution happens here. A validator's only job is to confirm
the payload is shaped correctly; it must not call out to any downstream
system.
"""

from __future__ import annotations

import enum
import threading
from dataclasses import dataclass
from typing import Any, Callable, Dict, Mapping, Optional, Tuple

from akaalIPC.protocol.errors import IPCError, IPCErrorCategory, make_error


class RequestKind(str, enum.Enum):
    COMMAND = "COMMAND"
    QUERY = "QUERY"


PayloadValidator = Callable[[Mapping[str, Any]], Optional[str]]
"""A validator returns ``None`` when the payload is valid, or a human-readable
rejection reason string when it is not. It must be a pure function of the
payload — no I/O, no downstream calls."""


@dataclass(frozen=True)
class SchemaDescriptor:
    request_type: str
    schema_version: str
    kind: RequestKind
    validator: PayloadValidator

    @property
    def key(self) -> Tuple[str, str]:
        return (self.request_type, self.schema_version)


class DuplicateSchemaRegistrationError(ValueError):
    pass


@dataclass(frozen=True)
class SchemaValidationResult:
    is_valid: bool
    descriptor: Optional[SchemaDescriptor] = None
    error: Optional[IPCError] = None


class SchemaRegistry:
    """Thread-safe registry of request-type/schema-version -> validator.

    A future Tauri command, REST endpoint, CLI verb, or Assistant tool call
    registers its request schema here exactly once at startup. The router
    never needs to know the concrete set of request types in advance.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._descriptors: Dict[Tuple[str, str], SchemaDescriptor] = {}

    def register(self, descriptor: SchemaDescriptor) -> None:
        with self._lock:
            if descriptor.key in self._descriptors:
                raise DuplicateSchemaRegistrationError(
                    f"Schema already registered for request_type="
                    f"{descriptor.request_type!r} schema_version={descriptor.schema_version!r}"
                )
            self._descriptors[descriptor.key] = descriptor

    def get(self, request_type: str, schema_version: str) -> Optional[SchemaDescriptor]:
        with self._lock:
            return self._descriptors.get((request_type, schema_version))

    def known_versions_for(self, request_type: str) -> Tuple[str, ...]:
        with self._lock:
            return tuple(
                version for (rtype, version) in self._descriptors if rtype == request_type
            )

    def validate(
        self,
        *,
        request_type: str,
        schema_version: str,
        kind: RequestKind,
        payload: Any,
        correlation_id: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> SchemaValidationResult:
        if not isinstance(payload, Mapping):
            return SchemaValidationResult(
                is_valid=False,
                error=make_error(
                    IPCErrorCategory.INVALID_REQUEST,
                    code="PAYLOAD_NOT_MAPPING",
                    message="Request payload must be a JSON object (mapping).",
                    correlation_id=correlation_id,
                    request_id=request_id,
                ),
            )

        descriptor = self.get(request_type, schema_version)
        if descriptor is None:
            known = self.known_versions_for(request_type)
            if known:
                return SchemaValidationResult(
                    is_valid=False,
                    error=make_error(
                        IPCErrorCategory.INVALID_SCHEMA,
                        code="SCHEMA_VERSION_INCOMPATIBLE",
                        message=(
                            f"request_type={request_type!r} has no registered schema "
                            f"version {schema_version!r}. Known versions: {known}."
                        ),
                        correlation_id=correlation_id,
                        request_id=request_id,
                        details={"known_schema_versions": list(known)},
                    ),
                )
            return SchemaValidationResult(
                is_valid=False,
                error=make_error(
                    IPCErrorCategory.INVALID_REQUEST,
                    code="UNKNOWN_REQUEST_TYPE",
                    message=f"No schema is registered for request_type={request_type!r}.",
                    correlation_id=correlation_id,
                    request_id=request_id,
                ),
            )

        if descriptor.kind != kind:
            return SchemaValidationResult(
                is_valid=False,
                error=make_error(
                    IPCErrorCategory.INVALID_REQUEST,
                    code="REQUEST_KIND_MISMATCH",
                    message=(
                        f"request_type={request_type!r} is registered as "
                        f"{descriptor.kind.value}, but request declared kind={kind.value}."
                    ),
                    correlation_id=correlation_id,
                    request_id=request_id,
                ),
            )

        rejection_reason = descriptor.validator(payload)
        if rejection_reason is not None:
            return SchemaValidationResult(
                is_valid=False,
                error=make_error(
                    IPCErrorCategory.INVALID_SCHEMA,
                    code="PAYLOAD_SCHEMA_REJECTED",
                    message=rejection_reason,
                    correlation_id=correlation_id,
                    request_id=request_id,
                ),
            )

        return SchemaValidationResult(is_valid=True, descriptor=descriptor)


def register_core_pipeline_schemas(registry: SchemaRegistry) -> None:
    """Registers standard P0-P6 command and query schemas into the SchemaRegistry."""
    def _require_migration_id(payload: Any) -> Optional[str]:
        if not isinstance(payload, Mapping) or "migration_id" not in payload:
            return "Payload must contain 'migration_id'."
        return None

    def _allow_any_mapping(payload: Any) -> Optional[str]:
        if not isinstance(payload, Mapping):
            return "Payload must be a JSON object (mapping)."
        return None

    # Commands
    cmd_types = [
        "migration.create", "migration.configure", "migration.plan", "migration.initialize",
        "migration.approve", "migration.start", "migration.cancel", "migration.recover",
        "migration.pause", "migration.resume", "migration.throttle_cdc",
        "fleet.drain_node", "fleet.undrain_node",
        "schedule.create", "schedule.update", "schedule.arm", "schedule.disable",
        "schedule.enable", "schedule.cancel", "schedule.delete", "retention.execute",
        "capacity.sample",
        "alert.rule.create", "alert.evaluate", "alert.acknowledge", "alert.resolve", "alert.suppress",
        "incident.create", "incident.alert.attach", "incident.status.update",
        "notification.send",
    ]
    for ct in cmd_types:
        try:
            registry.register(SchemaDescriptor(ct, "1.0", RequestKind.COMMAND, _allow_any_mapping))
        except DuplicateSchemaRegistrationError:
            pass

    # Queries
    query_types = [
        "migration.get", "migration.list", "operation.get", "mutability.evaluate",
        "observability.get", "health.get_explainable", "diagnostics.capture",
        "fleet.status", "metrics.export_prometheus",
        "schedule.get", "schedule.list", "schedule.occurrence.get", "schedule.occurrence.list",
        "retention.preview", "retention.operation.get", "retention.operation.list",
        "capacity.report", "capacity.history", "capacity.forecast",
        "alert.list", "alert.get",
        "incident.list", "incident.get", "incident.timeline",
        "notification.list",
    ]
    for qt in query_types:
        try:
            registry.register(SchemaDescriptor(qt, "1.0", RequestKind.QUERY, _allow_any_mapping))
        except DuplicateSchemaRegistrationError:
            pass

