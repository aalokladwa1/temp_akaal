"""
tests.unit.engine_extensions.test_configuration_schema
======================================================
Tests for declarative configuration schemas, typed field validation, bounds checking, and strict secret-reference enforcement.
"""

import pytest
from akaalEngine.extensions.configuration.validator import ConfigurationValidator
from akaalEngine.extensions.models.configuration import (
    ConfigurationConstraint,
    ConfigurationField,
    ConfigurationFieldType,
    ConfigurationSchema,
)
from akaalEngine.extensions.errors.taxonomy import ConfigurationValidationError


def test_configuration_schema_validation():
    schema = ConfigurationSchema(
        schema_id="postgres_options",
        fields=(
            ConfigurationField(
                name="host",
                field_type=ConfigurationFieldType.STRING,
                description="Hostname",
                is_required=True,
            ),
            ConfigurationField(
                name="port",
                field_type=ConfigurationFieldType.INTEGER,
                description="Port",
                is_required=True,
                default_value=5432,
                constraint=ConfigurationConstraint(min_value=1, max_value=65535),
            ),
            ConfigurationField(
                name="secret_ref",
                field_type=ConfigurationFieldType.SECRET_REF,
                description="Password Secret Ref",
                is_required=True,
            ),
        ),
    )

    # Valid configuration
    valid_cfg = {
        "host": "localhost",
        "port": 5432,
        "secret_ref": "vault://db/pg_pass",
    }
    ConfigurationValidator.validate(schema, valid_cfg)

    # Invalid port (out of bounds)
    invalid_port_cfg = {
        "host": "localhost",
        "port": 99999,
        "secret_ref": "vault://db/pg_pass",
    }
    with pytest.raises(ConfigurationValidationError) as exc_info:
        ConfigurationValidator.validate(schema, invalid_port_cfg)
    assert "greater than maximum" in str(exc_info.value)

    # Invalid type for host
    invalid_type_cfg = {
        "host": 12345,
        "port": 5432,
        "secret_ref": "vault://db/pg_pass",
    }
    with pytest.raises(ConfigurationValidationError) as exc_info:
        ConfigurationValidator.validate(schema, invalid_type_cfg)
    assert "must be a string" in str(exc_info.value)

    # Missing required field
    missing_cfg = {
        "port": 5432,
        "secret_ref": "vault://db/pg_pass",
    }
    with pytest.raises(ConfigurationValidationError) as exc_info:
        ConfigurationValidator.validate(schema, missing_cfg)
    assert "Required configuration field 'host' is missing" in str(exc_info.value)


def test_secret_ref_rejection_of_raw_multiline_and_bare_plaintext_secrets():
    schema = ConfigurationSchema(
        schema_id="auth_schema",
        fields=(
            ConfigurationField(
                name="api_token_ref",
                field_type=ConfigurationFieldType.SECRET_REF,
                description="Token Reference",
                is_required=True,
            ),
        ),
    )

    # 1. Valid pointer URIs are accepted
    ConfigurationValidator.validate(schema, {"api_token_ref": "vault://prod/keys/api"})
    ConfigurationValidator.validate(schema, {"api_token_ref": "env:API_TOKEN"})
    ConfigurationValidator.validate(schema, {"api_token_ref": "ref:sec_12345"})
    ConfigurationValidator.validate(schema, {"api_token_ref": "aws-sm:prod/db/secret"})

    # 2. Raw multiline key rejected
    raw_multiline_key = "-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA0...\n-----END RSA PRIVATE KEY-----"
    with pytest.raises(ConfigurationValidationError) as exc_info:
        ConfigurationValidator.validate(schema, {"api_token_ref": raw_multiline_key})
    assert "raw multiline secret material" in str(exc_info.value)

    # 3. Bare arbitrary plaintext string without reference URI scheme rejected
    with pytest.raises(ConfigurationValidationError) as exc_info2:
        ConfigurationValidator.validate(schema, {"api_token_ref": "MySuperSecretPassword123!"})
    assert "requires a valid secret pointer reference URI" in str(exc_info2.value)


def test_conditional_configuration_validation():
    from akaalEngine.extensions.models.configuration import ConfigurationCondition
    from akaalEngine.connection.models.endpoint import EndpointRole

    schema = ConfigurationSchema(
        schema_id="conditional_schema",
        fields=(
            ConfigurationField(
                name="auth_mode",
                field_type=ConfigurationFieldType.STRING,
                description="Authentication Mode",
                is_required=True,
            ),
            ConfigurationField(
                name="kerberos_keytab_ref",
                field_type=ConfigurationFieldType.SECRET_REF,
                description="Kerberos Keytab Reference",
                is_required=True,
                condition=ConfigurationCondition(
                    depends_on_field="auth_mode",
                    depends_on_value="KERBEROS",
                ),
            ),
        ),
    )

    # When auth_mode is PASSWORD, kerberos_keytab_ref is inactive and NOT required
    ConfigurationValidator.validate(schema, {"auth_mode": "PASSWORD"})

    # When auth_mode is KERBEROS, kerberos_keytab_ref IS active and REQUIRED
    with pytest.raises(ConfigurationValidationError) as exc_info:
        ConfigurationValidator.validate(schema, {"auth_mode": "KERBEROS"})
    assert "Required configuration field 'kerberos_keytab_ref' is missing" in str(exc_info.value)

    # When auth_mode is KERBEROS and kerberos_keytab_ref is provided with valid pointer URI, passes
    ConfigurationValidator.validate(
        schema,
        {"auth_mode": "KERBEROS", "kerberos_keytab_ref": "vault://k8s/keytab"},
    )
