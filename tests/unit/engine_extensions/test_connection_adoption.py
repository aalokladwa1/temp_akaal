"""
tests.unit.engine_extensions.test_connection_adoption
=====================================================
Tests verifying adoption of all 28 Connection providers from frozen Connection Authority.
"""

from akaalEngine.connection.catalog.provider_catalog import default_provider_catalog
from akaalEngine.extensions.authority import ExtensionsAuthority
from akaalEngine.extensions.models.identity import AuthorityId, ProviderId


from akaalEngine.extensions.errors.taxonomy import DependencyResolutionError


def test_connection_providers_adoption_completeness():
    ext_auth = ExtensionsAuthority.get_instance()
    adopted_provs = ext_auth.list_providers()

    assert len(adopted_provs) >= 28  # original Campaign A fleet; grows as P7A Campaign B adds providers

    expected_28 = [
        "sqlite", "postgresql", "mysql", "mariadb", "oracle", "mssql", "ibm_db2",
        "snowflake", "bigquery", "redshift", "databricks",
        "mongodb", "cassandra", "scylladb", "neo4j", "redis", "keydb", "elasticsearch", "opensearch",
        "kafka", "kinesis", "eventhubs", "pubsub",
        "s3", "gcs", "azure_blob", "minio", "hdfs",
    ]

    for expected_id in expected_28:
        assert expected_id in adopted_provs

    # SQLite has built-in driver, so it resolves cleanly
    handle_sqlite = ext_auth.resolve_strategy(
        provider_id="sqlite",
        authority_id="connection",
    )
    assert handle_sqlite.provider_id.value == "sqlite"
    assert handle_sqlite.authority_id.value == "connection"
    assert handle_sqlite.strategy_instance is not None
    handle_sqlite.release()


def test_adopted_provider_metadata_and_dependency_truth():
    ext_auth = ExtensionsAuthority.get_instance()

    # 1. SQLite has built-in standard library sqlite3 driver -> is_available=True
    sqlite_desc = ext_auth.describe_provider("sqlite")
    assert sqlite_desc is not None
    assert sqlite_desc.provider_id == "sqlite"
    assert sqlite_desc.vendor_name == "SQLite"
    assert sqlite_desc.family == "relational"
    assert "connection" in sqlite_desc.supported_authorities
    assert sqlite_desc.is_available is True
    assert len(sqlite_desc.missing_dependencies) == 0

    # 2. Dependency-gated provider (e.g. oracle) truthfully reports missing driver if not installed
    oracle_desc = ext_auth.describe_provider("oracle")
    assert oracle_desc is not None
    assert oracle_desc.provider_id == "oracle"
    assert "connection" in oracle_desc.supported_authorities
    # If oracledb is not installed in test environment:
    import importlib.util
    oracledb_installed = importlib.util.find_spec("oracledb") is not None
    if not oracledb_installed:
        assert oracle_desc.is_available is False
        assert "oracledb" in oracle_desc.missing_dependencies
        # Resolution fails closed on missing driver
        import pytest
        with pytest.raises(DependencyResolutionError):
            ext_auth.resolve_strategy("oracle", "connection")
    else:
        assert oracle_desc.is_available is True

    # 3. Missing oracle driver does NOT affect sqlite availability (isolation)
    assert sqlite_desc.is_available is True
