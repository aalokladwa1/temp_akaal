import pytest

from akaalIPC.protocol.envelopes import (
    CommandEnvelope,
    OperationReference,
    PayloadTypeError,
    QueryEnvelope,
    ResponseEnvelope,
    ResponseStatus,
    assert_json_safe,
)
from akaalIPC.protocol.errors import IPCError, IPCErrorCategory
from akaalIPC.protocol.schemas import RequestKind
from akaalIPC.security.context import ActorContext, ActorReference, CorrelationContext


def _actor():
    return ActorContext(actor=ActorReference(actor_id="u1", actor_type="user"))


def _corr():
    return CorrelationContext.new()


def test_command_envelope_requires_command_id():
    with pytest.raises(ValueError):
        CommandEnvelope(
            request_id="r1",
            protocol_version="1.0.0",
            schema_version="1.0",
            request_type="x",
            kind=RequestKind.COMMAND,
            actor=_actor(),
            correlation=_corr(),
            payload={},
            command_id="",
        )


def test_command_envelope_kind_mismatch_rejected():
    with pytest.raises(ValueError):
        CommandEnvelope(
            request_id="r1",
            protocol_version="1.0.0",
            schema_version="1.0",
            request_type="x",
            kind=RequestKind.QUERY,  # wrong on purpose
            actor=_actor(),
            correlation=_corr(),
            payload={},
            command_id="c1",
        )


def test_query_envelope_kind_mismatch_rejected():
    with pytest.raises(ValueError):
        QueryEnvelope(
            request_id="r1",
            protocol_version="1.0.0",
            schema_version="1.0",
            request_type="x",
            kind=RequestKind.COMMAND,  # wrong on purpose
            actor=_actor(),
            correlation=_corr(),
            payload={},
        )


def test_unknown_payload_cannot_smuggle_arbitrary_objects():
    class Dangerous:
        pass

    with pytest.raises(PayloadTypeError):
        assert_json_safe({"x": Dangerous()})


def test_json_safe_accepts_nested_primitives():
    assert_json_safe({"a": [1, 2, {"b": None, "c": True, "d": 1.5}], "e": "s"})


def test_payload_validated_at_construction_time():
    class NotJson:
        pass

    with pytest.raises(PayloadTypeError):
        QueryEnvelope(
            request_id="r1",
            protocol_version="1.0.0",
            schema_version="1.0",
            request_type="x",
            kind=RequestKind.QUERY,
            actor=_actor(),
            correlation=_corr(),
            payload={"bad": NotJson()},
        )


def test_response_envelope_requires_exactly_one_populated_field():
    with pytest.raises(ValueError):
        ResponseEnvelope(
            request_id="r1",
            correlation_id="c1",
            protocol_version="1.0.0",
            schema_version="1.0",
            response_type="x.response",
            status=ResponseStatus.OK,
            result=None,
        )


def test_response_envelope_rejects_multiple_populated_fields():
    error = IPCError(code="X", message="y", category=IPCErrorCategory.INTERNAL_ERROR)
    with pytest.raises(ValueError):
        ResponseEnvelope(
            request_id="r1",
            correlation_id="c1",
            protocol_version="1.0.0",
            schema_version="1.0",
            response_type="x.response",
            status=ResponseStatus.OK,
            result={"ok": True},
            error=error,
        )


def test_operation_reference_round_trip():
    op = OperationReference(
        operation_id="op-123",
        accepted_at="2026-08-20T00:00:00Z",
        query_request_type="widget.operation.status",
        correlation_id="corr-1",
        details={"phase": "STARTING"},
    )
    response = ResponseEnvelope(
        request_id="r1",
        correlation_id="corr-1",
        protocol_version="1.0.0",
        schema_version="1.0",
        response_type="widget.create.response",
        status=ResponseStatus.ACCEPTED,
        operation=op,
    )
    as_dict = response.to_dict()
    assert as_dict["operation"]["operation_id"] == "op-123"
    assert as_dict["operation"]["query_request_type"] == "widget.operation.status"
    assert as_dict["status"] == "ACCEPTED"
    # Round trip: nothing about RUNNING/COMPLETED/FAILED status is present —
    # IPC never infers operation lifecycle state.
    assert "status" not in as_dict["operation"]


def test_operation_reference_requires_query_request_type():
    with pytest.raises(ValueError):
        OperationReference(operation_id="op-1", accepted_at="now", query_request_type="")
