"""
akaalPipeline.api.rest.errors
================================
Maps canonical akaalIPC IPCError categories to stable external HTTP status codes.
Never leaks stack traces, internal paths, or secrets -- IPCError.details is already
sanitized at construction (akaalIPC.protocol.errors._sanitize_details), and this
module surfaces exactly that sanitized shape and nothing else.
"""

from __future__ import annotations

from akaalIPC.protocol.errors import IPCError, IPCErrorCategory

_CATEGORY_TO_STATUS = {
    IPCErrorCategory.INVALID_REQUEST: 400,
    IPCErrorCategory.INVALID_SCHEMA: 400,
    IPCErrorCategory.PROTOCOL_INCOMPATIBLE: 400,
    IPCErrorCategory.UNSUPPORTED: 400,
    IPCErrorCategory.UNBOUND: 404,
    IPCErrorCategory.UNAVAILABLE: 503,
    IPCErrorCategory.NOT_READY: 409,
    IPCErrorCategory.INELIGIBLE: 409,
    IPCErrorCategory.UNAUTHORIZED: 401,
    IPCErrorCategory.FORBIDDEN: 403,
    IPCErrorCategory.REVISION_CONFLICT: 409,
    IPCErrorCategory.IDEMPOTENCY_CONFLICT: 409,
    IPCErrorCategory.TIMEOUT: 504,
    IPCErrorCategory.CANCELLED: 409,
    IPCErrorCategory.STALE_RESULT: 409,
    IPCErrorCategory.INTERNAL_ERROR: 500,
}


def http_status_for(error: IPCError) -> int:
    return _CATEGORY_TO_STATUS.get(error.category, 500)


def error_body(error: IPCError) -> dict:
    """
    A stable external error shape. Deliberately omits nothing beyond what IPCError.to_dict()
    already exposes (code/message/category/retryable/correlation_id/request_id/operation_id/
    sanitized details) -- no stack traces, no internal identifiers beyond these, no secrets.
    """
    return error.to_dict()
