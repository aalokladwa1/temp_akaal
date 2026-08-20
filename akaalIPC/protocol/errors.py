"""
akaalIPC.protocol.errors
==========================
Transport-neutral, IPC-safe structured error taxonomy.

This is the ONLY error shape that crosses the akaalIPC boundary. Every
failure — protocol-level, schema-level, downstream-mapped, or an unexpected
internal exception — is converted into an ``IPCError`` before it reaches a
caller. Nothing crosses this boundary as a raw exception, a stack trace, or
a bare dict.

Fail-closed rule: an unbound or unavailable downstream dependency is not an
exception to be swallowed into a manufactured success — it is one of the
categories below (``UNBOUND`` / ``UNAVAILABLE`` / ``NOT_READY``), returned
explicitly.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any, Mapping, Optional


class IPCErrorCategory(str, enum.Enum):
    INVALID_REQUEST = "INVALID_REQUEST"
    INVALID_SCHEMA = "INVALID_SCHEMA"
    PROTOCOL_INCOMPATIBLE = "PROTOCOL_INCOMPATIBLE"
    UNSUPPORTED = "UNSUPPORTED"
    UNBOUND = "UNBOUND"
    UNAVAILABLE = "UNAVAILABLE"
    NOT_READY = "NOT_READY"
    INELIGIBLE = "INELIGIBLE"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    REVISION_CONFLICT = "REVISION_CONFLICT"
    IDEMPOTENCY_CONFLICT = "IDEMPOTENCY_CONFLICT"
    TIMEOUT = "TIMEOUT"
    CANCELLED = "CANCELLED"
    STALE_RESULT = "STALE_RESULT"
    INTERNAL_ERROR = "INTERNAL_ERROR"


# Categories that are safe to retry blindly from the caller's perspective.
_RETRYABLE_CATEGORIES = frozenset(
    {
        IPCErrorCategory.UNAVAILABLE,
        IPCErrorCategory.NOT_READY,
        IPCErrorCategory.TIMEOUT,
        IPCErrorCategory.INTERNAL_ERROR,
    }
)

# Field names that must never appear in a caller-visible error's details,
# even if a downstream layer's error accidentally included them.
_FORBIDDEN_DETAIL_KEYS = frozenset(
    {
        "password",
        "passwd",
        "secret",
        "token",
        "api_key",
        "apikey",
        "credential",
        "credentials",
        "connection_string",
        "dsn",
        "private_key",
        "stack_trace",
        "traceback",
    }
)


def _sanitize_details(details: Optional[Mapping[str, Any]]) -> Mapping[str, Any]:
    if not details:
        return {}
    safe: dict[str, Any] = {}
    for key, value in details.items():
        lowered = key.lower()
        if any(bad in lowered for bad in _FORBIDDEN_DETAIL_KEYS):
            continue
        if isinstance(value, (str, int, float, bool)) or value is None:
            safe[key] = value
        elif isinstance(value, (list, tuple)):
            safe[key] = [v for v in value if isinstance(v, (str, int, float, bool)) or v is None]
        elif isinstance(value, Mapping):
            safe[key] = _sanitize_details(value)
        # Anything else (objects, exceptions, callables) is dropped rather
        # than risking leakage of an unreviewed __repr__.
    return safe


@dataclass(frozen=True)
class IPCError(Exception):
    """A single structured, transport-safe error.

    Deliberately a dataclass (not a rich exception hierarchy) so it can be
    serialized identically regardless of whether it was raised internally
    or constructed directly by the router while mapping a downstream
    failure.
    """

    code: str
    message: str
    category: IPCErrorCategory
    retryable: bool = False
    correlation_id: Optional[str] = None
    request_id: Optional[str] = None
    operation_id: Optional[str] = None
    details: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "details", _sanitize_details(self.details))

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "message": self.message,
            "category": self.category.value,
            "retryable": self.retryable,
            "correlation_id": self.correlation_id,
            "request_id": self.request_id,
            "operation_id": self.operation_id,
            "details": dict(self.details),
        }

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"[{self.category.value}] {self.code}: {self.message}"


def make_error(
    category: IPCErrorCategory,
    code: str,
    message: str,
    *,
    correlation_id: Optional[str] = None,
    request_id: Optional[str] = None,
    operation_id: Optional[str] = None,
    details: Optional[Mapping[str, Any]] = None,
    retryable: Optional[bool] = None,
) -> IPCError:
    return IPCError(
        code=code,
        message=message,
        category=category,
        retryable=category in _RETRYABLE_CATEGORIES if retryable is None else retryable,
        correlation_id=correlation_id,
        request_id=request_id,
        operation_id=operation_id,
        details=details or {},
    )


def unbound_error(component: str, *, correlation_id: Optional[str] = None, request_id: Optional[str] = None) -> IPCError:
    """The correct response when a required downstream port has no production binding."""
    return make_error(
        IPCErrorCategory.UNBOUND,
        code="DOWNSTREAM_UNBOUND",
        message=f"No production binding is configured for '{component}'.",
        correlation_id=correlation_id,
        request_id=request_id,
        details={"component": component},
    )


def sanitize_unexpected_exception(
    exc: BaseException,
    *,
    correlation_id: Optional[str] = None,
    request_id: Optional[str] = None,
) -> IPCError:
    """Convert any unexpected exception into a sanitized INTERNAL_ERROR.

    Never re-raises, never returns success, never leaks the exception's
    message verbatim (exception messages may contain connection strings,
    file paths, or credentials) — only the exception's class name is kept.
    """
    return make_error(
        IPCErrorCategory.INTERNAL_ERROR,
        code="INTERNAL_ERROR",
        message="An unexpected internal error occurred while processing the request.",
        correlation_id=correlation_id,
        request_id=request_id,
        details={"exception_type": type(exc).__name__},
        retryable=True,
    )
