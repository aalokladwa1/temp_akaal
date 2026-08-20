from akaalIPC.protocol.errors import (
    IPCError,
    IPCErrorCategory,
    make_error,
    sanitize_unexpected_exception,
    unbound_error,
)


def test_unbound_error_shape():
    err = unbound_error("UnifiedCallerPort", correlation_id="c1", request_id="r1")
    assert err.category == IPCErrorCategory.UNBOUND
    assert err.correlation_id == "c1"
    assert err.request_id == "r1"
    assert err.details["component"] == "UnifiedCallerPort"


def test_unexpected_exception_never_becomes_success_and_is_sanitized():
    try:
        raise RuntimeError("connection string: postgres://user:hunter2@host/db")
    except RuntimeError as exc:
        err = sanitize_unexpected_exception(exc, correlation_id="c1", request_id="r1")

    assert err.category == IPCErrorCategory.INTERNAL_ERROR
    # The raw exception message (which may contain credentials) must never
    # be forwarded verbatim across the boundary.
    assert "hunter2" not in err.message
    assert "hunter2" not in str(err.details)
    assert err.details["exception_type"] == "RuntimeError"


def test_sensitive_detail_keys_are_stripped():
    err = make_error(
        IPCErrorCategory.INTERNAL_ERROR,
        code="X",
        message="failure",
        details={"password": "secret123", "safe_field": "kept", "api_key": "abc"},
    )
    assert "password" not in err.details
    assert "api_key" not in err.details
    assert err.details["safe_field"] == "kept"


def test_non_primitive_detail_values_are_dropped_not_leaked():
    class Opaque:
        def __repr__(self):
            return "<Opaque secret=xyz>"

    err = make_error(
        IPCErrorCategory.INTERNAL_ERROR, code="X", message="failure", details={"obj": Opaque()}
    )
    assert "obj" not in err.details


def test_retryable_defaults_by_category():
    unavailable = make_error(IPCErrorCategory.UNAVAILABLE, code="X", message="m")
    invalid = make_error(IPCErrorCategory.INVALID_REQUEST, code="X", message="m")
    assert unavailable.retryable is True
    assert invalid.retryable is False


def test_ipc_error_is_raisable_and_catchable():
    err = IPCError(code="X", message="m", category=IPCErrorCategory.TIMEOUT)
    try:
        raise err
    except IPCError as caught:
        assert caught.code == "X"
        assert caught.to_dict()["category"] == "TIMEOUT"


def test_to_dict_never_includes_stack_trace_field():
    err = make_error(IPCErrorCategory.INTERNAL_ERROR, code="X", message="m")
    assert "stack_trace" not in err.to_dict()
    assert "traceback" not in err.to_dict()
