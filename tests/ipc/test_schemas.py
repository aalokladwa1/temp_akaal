import pytest

from akaalIPC.protocol.errors import IPCErrorCategory
from akaalIPC.protocol.schemas import (
    DuplicateSchemaRegistrationError,
    RequestKind,
    SchemaDescriptor,
    SchemaRegistry,
)


def _always_valid(payload):
    return None


def test_duplicate_schema_registration_rejected():
    registry = SchemaRegistry()
    registry.register(SchemaDescriptor("foo", "1.0", RequestKind.QUERY, _always_valid))
    with pytest.raises(DuplicateSchemaRegistrationError):
        registry.register(SchemaDescriptor("foo", "1.0", RequestKind.QUERY, _always_valid))


def test_unknown_request_type_rejected():
    registry = SchemaRegistry()
    result = registry.validate(
        request_type="does.not.exist", schema_version="1.0", kind=RequestKind.QUERY, payload={}
    )
    assert not result.is_valid
    assert result.error.code == "UNKNOWN_REQUEST_TYPE"
    assert result.error.category == IPCErrorCategory.INVALID_REQUEST


def test_incompatible_schema_version_rejected():
    registry = SchemaRegistry()
    registry.register(SchemaDescriptor("foo", "1.0", RequestKind.QUERY, _always_valid))
    result = registry.validate(
        request_type="foo", schema_version="2.0", kind=RequestKind.QUERY, payload={}
    )
    assert not result.is_valid
    assert result.error.code == "SCHEMA_VERSION_INCOMPATIBLE"
    assert result.error.category == IPCErrorCategory.INVALID_SCHEMA
    assert result.error.details["known_schema_versions"] == ["1.0"]


def test_payload_must_be_a_mapping():
    registry = SchemaRegistry()
    registry.register(SchemaDescriptor("foo", "1.0", RequestKind.QUERY, _always_valid))
    result = registry.validate(
        request_type="foo", schema_version="1.0", kind=RequestKind.QUERY, payload=["not", "a", "dict"]
    )
    assert not result.is_valid
    assert result.error.code == "PAYLOAD_NOT_MAPPING"


def test_request_kind_mismatch_rejected():
    registry = SchemaRegistry()
    registry.register(SchemaDescriptor("foo", "1.0", RequestKind.COMMAND, _always_valid))
    result = registry.validate(
        request_type="foo", schema_version="1.0", kind=RequestKind.QUERY, payload={}
    )
    assert not result.is_valid
    assert result.error.code == "REQUEST_KIND_MISMATCH"


def test_validator_rejection_surfaces_as_invalid_schema():
    def reject_missing_field(payload):
        return None if "id" in payload else "missing 'id'"

    registry = SchemaRegistry()
    registry.register(SchemaDescriptor("foo", "1.0", RequestKind.QUERY, reject_missing_field))
    result = registry.validate(
        request_type="foo", schema_version="1.0", kind=RequestKind.QUERY, payload={}
    )
    assert not result.is_valid
    assert result.error.category == IPCErrorCategory.INVALID_SCHEMA
    assert result.error.message == "missing 'id'"


def test_valid_payload_passes():
    registry = SchemaRegistry()
    registry.register(SchemaDescriptor("foo", "1.0", RequestKind.QUERY, _always_valid))
    result = registry.validate(
        request_type="foo", schema_version="1.0", kind=RequestKind.QUERY, payload={"any": "thing"}
    )
    assert result.is_valid
    assert result.descriptor.request_type == "foo"
