"""
tests.unit.engine_extensions.test_sensitive_sanitization
========================================================
Tests for sanitizing configuration schemas and error messages to prevent credential leakage.
"""

from akaalEngine.extensions.configuration.sanitizer import ConfigurationSanitizer
from akaalEngine.extensions.errors.sanitization import sanitize_error_message
from akaalEngine.extensions.models.configuration import (
    ConfigurationField,
    ConfigurationFieldType,
    ConfigurationSchema,
)


def test_schema_sanitization_and_sensitive_flag():
    schema = ConfigurationSchema(
        schema_id="test_schema",
        fields=(
            ConfigurationField(
                name="username",
                field_type=ConfigurationFieldType.STRING,
                description="User",
                default_value="postgres",
            ),
            ConfigurationField(
                name="secret_key_ref",
                field_type=ConfigurationFieldType.SECRET_REF,
                description="Secret Pointer",
                default_value="vault:secret",
            ),
        ),
    )

    sanitized = ConfigurationSanitizer.sanitize_schema(schema)
    dict_repr = sanitized.to_dict()

    assert dict_repr["schema_id"] == "test_schema"
    assert len(dict_repr["fields"]) == 2

    # Verify sensitive default is redacted on the DTO instance itself
    secret_dto = [f for f in sanitized.fields if f.name == "secret_key_ref"][0]
    assert secret_dto.is_sensitive is True
    assert secret_dto.default_value == "<REDACTED>"

    # Verify dict representation
    secret_field = [f for f in dict_repr["fields"] if f["name"] == "secret_key_ref"][0]
    assert secret_field["is_sensitive"] is True
    assert secret_field["default_value"] == "<REDACTED>"


def test_error_message_sanitization():
    raw_error = "Connection failed for user=admin password=SecretPassword123! token=abc123xyz"
    sanitized = sanitize_error_message(raw_error)
    assert "SecretPassword123!" not in sanitized
    assert "password=***REDACTED***" in sanitized
