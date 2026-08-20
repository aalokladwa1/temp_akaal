from akaalIPC.protocol.errors import IPCErrorCategory
from akaalIPC.protocol.versions import (
    CURRENT_PROTOCOL_VERSION,
    SUPPORTED_PROTOCOL_VERSIONS,
    check_protocol_compatibility,
)


def test_current_version_is_supported():
    assert CURRENT_PROTOCOL_VERSION in SUPPORTED_PROTOCOL_VERSIONS


def test_supported_version_is_compatible():
    result = check_protocol_compatibility(CURRENT_PROTOCOL_VERSION)
    assert result.is_compatible
    assert result.negotiated_version == CURRENT_PROTOCOL_VERSION
    assert result.error is None


def test_unsupported_version_is_rejected_not_coerced():
    result = check_protocol_compatibility("99.0.0")
    assert not result.is_compatible
    assert result.negotiated_version is None
    assert result.error.category == IPCErrorCategory.PROTOCOL_INCOMPATIBLE
    assert result.error.code == "PROTOCOL_VERSION_UNSUPPORTED"


def test_missing_version_is_rejected():
    result = check_protocol_compatibility("")
    assert not result.is_compatible
    assert result.error.code == "PROTOCOL_VERSION_MISSING"


def test_no_silent_coercion_across_major_versions():
    # A caller declaring an old/future-major version must never be
    # silently treated as the current version.
    result = check_protocol_compatibility("2.0.0")
    assert not result.is_compatible
    assert result.requested_version == "2.0.0"
