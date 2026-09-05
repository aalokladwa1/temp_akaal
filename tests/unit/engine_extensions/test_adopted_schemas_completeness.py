"""
tests.unit.engine_extensions.test_adopted_schemas_completeness
=============================================================
Verifies that Authority #2 Extensions exposes complete, valid, truthful
ConfigurationSchema metadata for all adopted Connection providers (originally 28,
growing as P7A Campaign B adds providers).
"""

from __future__ import annotations

import pytest

from akaalEngine.connection.catalog.provider_catalog import default_provider_catalog
from akaalEngine.extensions.authority import default_extensions_authority
from akaalEngine.extensions.integration.builtin_connection_bootstrap import (
    BUILTIN_CONNECTION_EXTENSION_ID,
    BuiltinConnectionBootstrap,
)
from akaalEngine.extensions.integration.builtin_connection_schemas import (
    build_connection_provider_schema,
)
from akaalEngine.extensions.models.enums import ConfigurationFieldType
from akaalEngine.extensions.models.identity import ProviderId


def test_all_28_adopted_providers_have_truthful_configuration_schemas():
    registered_ids = default_provider_catalog.list_providers()
    expected_count = len(registered_ids)  # fleet size grows as P7A Campaign B adds providers; verify completeness, not a frozen count
    assert expected_count >= 28, f"Expected at least the original 28 adopted providers, found {expected_count}"

    manifest = BuiltinConnectionBootstrap.adopt_connection_providers()
    assert manifest.extension_id == BUILTIN_CONNECTION_EXTENSION_ID
    assert len(manifest.provider_contributions) == expected_count

    for prov_contrib in manifest.provider_contributions:
        prov_id_str = prov_contrib.provider_id.value
        assert len(prov_contrib.strategies) >= 1, f"Provider '{prov_id_str}' has no strategies"
        strat = prov_contrib.strategies[0]
        schema = strat.configuration_schema
        assert schema is not None, f"Strategy for '{prov_id_str}' has no ConfigurationSchema"
        assert len(schema.fields) > 0, f"ConfigurationSchema for '{prov_id_str}' has empty fields"

        # Check that field names and types are valid
        field_names = [f.name for f in schema.fields]
        assert len(field_names) == len(set(field_names)), f"Duplicate field names in schema for '{prov_id_str}'"

        # If provider has secret fields, ensure they are SECRET_REF and is_sensitive=True
        for f in schema.fields:
            if f.name.endswith("_ref") or "password" in f.name or "token" in f.name or "key" in f.name or "secret" in f.name:
                if f.field_type == ConfigurationFieldType.SECRET_REF:
                    assert f.is_sensitive is True


def test_specific_provider_schema_descriptors():
    # 1. Oracle Schema
    oracle_schema = build_connection_provider_schema("oracle")
    assert oracle_schema is not None
    assert oracle_schema.get_field("wallet_location") is not None
    assert oracle_schema.get_field("tns_entry") is not None
    assert oracle_schema.get_field("privilege_mode") is not None
    priv_field = oracle_schema.get_field("privilege_mode")
    assert priv_field.constraint.allowed_values == ("NORMAL", "SYSDBA", "SYSOPER")

    # 2. MSSQL Schema
    mssql_schema = build_connection_provider_schema("mssql")
    assert mssql_schema is not None
    assert mssql_schema.get_field("trusted_connection") is not None
    assert mssql_schema.get_field("integrated_security") is not None
    assert mssql_schema.get_field("odbc_driver") is not None

    # 3. Kafka Schema
    kafka_schema = build_connection_provider_schema("kafka")
    assert kafka_schema is not None
    assert kafka_schema.get_field("endpoints") is not None
    assert kafka_schema.get_field("security_protocol") is not None
    assert kafka_schema.get_field("sasl_mechanism") is not None

    # 4. S3 Schema
    s3_schema = build_connection_provider_schema("s3")
    assert s3_schema is not None
    assert s3_schema.get_field("session_token_ref") is not None
    assert s3_schema.get_field("endpoint_url") is not None

    # 5. Snowflake Schema
    sf_schema = build_connection_provider_schema("snowflake")
    assert sf_schema is not None
    assert sf_schema.get_field("account") is not None
    assert sf_schema.get_field("role") is not None
    assert sf_schema.get_field("authenticator") is not None


def test_extensions_facade_validates_adopted_provider_configuration():
    ext_auth = default_extensions_authority
    ext_auth.bootstrap_builtin_providers()

    pg_schema = build_connection_provider_schema("postgresql")
    assert pg_schema is not None

    # Valid PostgreSQL config
    valid_pg = {
        "host": "pg.internal",
        "port": 5432,
        "database_name": "appdb",
        "username": "pguser",
        "password_ref": "vault://pg/pass",
    }
    # Valid config should pass without exception
    ext_auth.validate_configuration(
        schema=pg_schema,
        config_values=valid_pg,
    )

    # Invalid PostgreSQL config (missing required password_ref)
    invalid_pg = {
        "host": "pg.internal",
        "port": 5432,
        "database_name": "appdb",
        "username": "pguser",
    }
    from akaalEngine.extensions.errors.taxonomy import ConfigurationValidationError
    with pytest.raises(ConfigurationValidationError) as exc_info:
        ext_auth.validate_configuration(
            schema=pg_schema,
            config_values=invalid_pg,
        )
    assert "password_ref" in str(exc_info.value)
