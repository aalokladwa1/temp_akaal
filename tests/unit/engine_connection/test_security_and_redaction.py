"""
Unit tests for akaalEngine.connection.security
==============================================
Verifies secret redaction, ephemeral reference resolution, and TLS context construction.
"""

import pytest

from akaalEngine.connection.models.endpoint import (
    AuthenticationSpec,
    AuthenticationType,
    EndpointSpec,
    TLSBinding,
    TLSMode,
)
from akaalEngine.connection.security.authentication import AuthenticationManager
from akaalEngine.connection.security.redaction import (
    REDACTED_PLACEHOLDER,
    is_sensitive_key,
    redact_mapping,
    redact_text,
    redact_url,
)
from akaalEngine.connection.security.secret_consumer import (
    ResolvedSecret,
    SecretConsumer,
)
from akaalEngine.connection.security.tls import TLSContextBuilder


def test_redact_text():
    raw_text = "Connection string: postgresql://admin:super_secret_password_123@db.example.com:5432/proddb"
    redacted = redact_text(raw_text)
    assert "super_secret_password_123" not in redacted
    assert "admin:[REDACTED]@db.example.com:5432/proddb" in redacted

    inline_text = "Failed with password=MySecretPassword123 and token=BEARER_TOKEN_ABC"
    redacted_inline = redact_text(inline_text)
    assert "MySecretPassword123" not in redacted_inline
    assert "BEARER_TOKEN_ABC" not in redacted_inline


def test_redact_mapping():
    data = {
        "host": "localhost",
        "port": 5432,
        "password": "my_password",
        "client_secret": "my_client_secret",
        "nested": {
            "api_key": "key123",
            "normal_field": "visible",
        },
    }
    redacted = redact_mapping(data)
    assert redacted["host"] == "localhost"
    assert redacted["password"] == REDACTED_PLACEHOLDER
    assert redacted["client_secret"] == REDACTED_PLACEHOLDER
    assert redacted["nested"]["api_key"] == REDACTED_PLACEHOLDER
    assert redacted["nested"]["normal_field"] == "visible"


def test_safe_repr_mixin():
    auth = AuthenticationSpec(
        auth_type=AuthenticationType.PASSWORD,
        username="user1",
        secret_ref="vault://secret/1",
        additional_params={"password": "raw_pass_leaked"},
    )
    repr_str = repr(auth)
    assert "raw_pass_leaked" not in repr_str
    assert REDACTED_PLACEHOLDER in repr_str


def test_resolved_secret_lifecycle():
    secret = ResolvedSecret(secret_value="plaintext_password", reference_id="ref-123")
    assert secret.is_valid() is True
    assert secret.get_value() == "plaintext_password"

    # Test context manager wipe
    with secret as s:
        assert s.get_value() == "plaintext_password"

    assert secret.is_valid() is False
    with pytest.raises(RuntimeError):
        secret.get_value()


def test_secret_consumer_rotation_notification():
    consumer = SecretConsumer()
    rotated_events = []

    def on_rotate(ref_id, version):
        rotated_events.append((ref_id, version))

    consumer.register_rotation_listener(on_rotate)
    consumer.notify_rotation("vault://db/password", "2")

    assert len(rotated_events) == 1
    assert rotated_events[0] == ("vault://db/password", "2")


def test_tls_context_builder():
    builder = TLSContextBuilder()
    # Disabled mode returns None
    disabled_binding = TLSBinding(mode=TLSMode.DISABLED)
    assert builder.build_ssl_context(disabled_binding) is None

    # Full verification mode builds standard context
    full_binding = TLSBinding(mode=TLSMode.VERIFY_FULL, tls_min_version="TLSv1.2")
    ctx = builder.build_ssl_context(full_binding)
    assert ctx is not None
    assert ctx.check_hostname is True
