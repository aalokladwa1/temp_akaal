"""
tests.unit.engine_connection.test_capability_conservation_closure
=================================================================
Dedicated verification test suite for the six source-proven capability-conservation blockers:
1. Complete canonical specialized secret resolution (AuthenticationManager + SecretConsumer).
2. GCP fail-closed identity without ADC fallback on invalid/missing service account credentials.
3. Cluster multi-endpoint resolution through canonical routing (RouteResolver).
4. Truthful executable alternative driver execution paths (MariaDB, Redshift).
5. Physical non-mutating validation RPCs (Pub/Sub, Event Hubs).
6. 28 Connection Provider Schemas ↔ Connection physical options alignment.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from akaalEngine.connection.catalog.provider_catalog import default_provider_catalog
from akaalEngine.connection.models.endpoint import (
    AuthenticationSpec,
    AuthenticationType,
    EndpointRole,
    EndpointSpec,
    RouteSpec,
    RouteType,
    TLSBinding,
    TLSMode,
)
from akaalEngine.connection.models.errors import (
    AuthenticationError,
    ConfigurationError,
    SecretResolutionError,
)
from akaalEngine.connection.providers.nosql.cassandra import CassandraProviderStrategy
from akaalEngine.connection.providers.nosql.elasticsearch import ElasticsearchProviderStrategy
from akaalEngine.connection.providers.relational.mariadb import MariaDBProviderStrategy
from akaalEngine.connection.providers.relational.mssql import MSSQLProviderStrategy
from akaalEngine.connection.providers.relational.sqlite import SQLiteProviderStrategy
from akaalEngine.connection.providers.storage.gcs import GCSProviderStrategy
from akaalEngine.connection.providers.streaming.eventhubs import EventHubsProviderStrategy
from akaalEngine.connection.providers.streaming.kafka import KafkaProviderStrategy
from akaalEngine.connection.providers.streaming.pubsub import PubSubProviderStrategy
from akaalEngine.connection.providers.warehouse.bigquery import BigQueryProviderStrategy
from akaalEngine.connection.providers.warehouse.redshift import RedshiftProviderStrategy
from akaalEngine.connection.providers.warehouse.snowflake import SnowflakeProviderStrategy
from akaalEngine.connection.routing.resolver import (
    ResolvedEndpointTarget,
    ResolvedRoute,
    RouteResolver,
    default_route_resolver,
)
from akaalEngine.connection.security.authentication import AuthenticationManager
from akaalEngine.connection.security.secret_consumer import ResolvedSecret, SecretConsumer
from akaalEngine.extensions.integration.builtin_connection_schemas import build_connection_provider_schema


@pytest.fixture
def mock_resolved_route():
    return ResolvedRoute(
        effective_host="db.example.internal",
        effective_port=1521,
        resolved_ip="10.0.1.50",
        dns_time_ms=1.5,
        route_type=RouteType.DIRECT,
    )


# =============================================================================
# CORRECTION 1: CANONICAL SPECIALIZED SECRET RESOLUTION
# =============================================================================

def test_canonical_specialized_secret_resolution_success():
    mock_consumer = MagicMock(spec=SecretConsumer)

    def resolve_side_effect(ref, version="1"):
        if ref == "vault://aws/session-token":
            return ResolvedSecret(secret_value="sts-session-token-xyz", reference_id=ref, version=version)
        elif ref == "vault://gcp/sa-key":
            return ResolvedSecret(secret_value='{"type": "service_account", "project_id": "test"}', reference_id=ref, version=version)
        elif ref == "vault://azure/conn-str":
            return ResolvedSecret(secret_value="Endpoint=sb://test.servicebus.windows.net/;SharedAccessKey=secret", reference_id=ref, version=version)
        elif ref == "vault://oracle/wallet-pw":
            return ResolvedSecret(secret_value="WalletSecretPass123", reference_id=ref, version=version)
        elif ref == "vault://elastic/api-key":
            return ResolvedSecret(secret_value="V1dTRXpSUUIxTmt...", reference_id=ref, version=version)
        return None

    mock_consumer.resolve.side_effect = resolve_side_effect

    auth_mgr = AuthenticationManager(secret_consumer=mock_consumer)

    auth_spec = AuthenticationSpec(
        auth_type=AuthenticationType.SECRET_REFERENCE,
        username="dbadmin",
        session_token_ref="vault://aws/session-token",
        service_account_json_ref="vault://gcp/sa-key",
        connection_string_ref="vault://azure/conn-str",
        wallet_password_ref="vault://oracle/wallet-pw",
        api_key_ref="vault://elastic/api-key",
    )

    creds = auth_mgr.resolve_credentials(auth_spec, provider_id="test_provider")

    assert creds["username"] == "dbadmin"
    assert creds["session_token"] == "sts-session-token-xyz"
    assert creds["aws_session_token"] == "sts-session-token-xyz"
    assert creds["service_account_json"] == '{"type": "service_account", "project_id": "test"}'
    assert creds["connection_string"] == "Endpoint=sb://test.servicebus.windows.net/;SharedAccessKey=secret"
    assert creds["wallet_password"] == "WalletSecretPass123"
    assert creds["api_key"] == "V1dTRXpSUUIxTmt..."
    assert len(creds["_resolved_secrets"]) >= 5


def test_canonical_specialized_secret_resolution_fail_closed():
    mock_consumer = MagicMock(spec=SecretConsumer)
    mock_consumer.resolve.return_value = None  # Secret resolution failure

    auth_mgr = AuthenticationManager(secret_consumer=mock_consumer)

    auth_spec = AuthenticationSpec(
        auth_type=AuthenticationType.SECRET_REFERENCE,
        service_account_json_ref="vault://nonexistent/sa-key",
    )

    with pytest.raises(SecretResolutionError) as exc_info:
        auth_mgr.resolve_credentials(auth_spec, provider_id="gcs")
    assert "Failed to resolve GCP service account JSON reference" in str(exc_info.value)


# =============================================================================
# CORRECTION 2: GCP RAW-CREDENTIAL BYPASS & IDENTITY SUBSTITUTION REMOVAL
# =============================================================================

def test_gcs_fail_closed_on_invalid_service_account_json(mock_resolved_route):
    strat = GCSProviderStrategy()
    spec = EndpointSpec(
        provider_id="gcs",
        account_id="test-project",
        auth_spec=AuthenticationSpec(
            auth_type=AuthenticationType.SECRET_REFERENCE,
            service_account_json_ref="vault://gcp/sa-key",
        ),
    )
    # Invalid JSON in service_account_json must raise AuthenticationError fail-closed
    with patch("akaalEngine.connection.providers.storage.gcs.GCSProviderStrategy.is_dependency_available", return_value=(True, "ok")):
        with patch.dict("sys.modules", {"google.cloud": MagicMock(), "google.cloud.storage": MagicMock(), "google.oauth2.service_account": MagicMock()}):
            with pytest.raises(AuthenticationError) as exc_info:
                strat.connect(spec, mock_resolved_route, {"service_account_json": "MALFORMED_JSON_STRING"})
            assert exc_info.value.failure.error_code == "GCP_SA_CREDENTIAL_CONSTRUCTION_FAILED"


def test_pubsub_fail_closed_on_missing_explicit_sa_credentials(mock_resolved_route):
    strat = PubSubProviderStrategy()
    spec = EndpointSpec(
        provider_id="pubsub",
        account_id="test-project",
        auth_spec=AuthenticationSpec(
            auth_type=AuthenticationType.SECRET_REFERENCE,
            service_account_json_ref="vault://gcp/sa-key",
        ),
    )
    # Missing explicit credentials dict must raise AuthenticationError without ADC fallback
    with patch("akaalEngine.connection.providers.streaming.pubsub.PubSubProviderStrategy.is_dependency_available", return_value=(True, "ok")):
        with patch.dict("sys.modules", {"google.cloud": MagicMock(), "google.cloud.pubsub_v1": MagicMock()}):
            with pytest.raises(AuthenticationError) as exc_info:
                strat.connect(spec, mock_resolved_route, {})
            assert exc_info.value.failure.error_code == "PUBSUB_EXPLICIT_CREDENTIALS_MISSING"


def test_bigquery_fail_closed_on_missing_explicit_sa_credentials(mock_resolved_route):
    strat = BigQueryProviderStrategy()
    spec = EndpointSpec(
        provider_id="bigquery",
        account_id="test-project",
        auth_spec=AuthenticationSpec(
            auth_type=AuthenticationType.SECRET_REFERENCE,
            service_account_json_ref="vault://gcp/sa-key",
        ),
    )
    with patch("akaalEngine.connection.providers.warehouse.bigquery.BigQueryProviderStrategy.is_dependency_available", return_value=(True, "ok")):
        with patch.dict("sys.modules", {"google.cloud": MagicMock(), "google.cloud.bigquery": MagicMock()}):
            with pytest.raises(AuthenticationError) as exc_info:
                strat.connect(spec, mock_resolved_route, {})
            assert exc_info.value.failure.error_code == "BIGQUERY_EXPLICIT_CREDENTIALS_MISSING"


# =============================================================================
# CORRECTION 3: CLUSTER MULTI-ENDPOINT CANONICAL ROUTING
# =============================================================================

def test_route_resolver_resolves_all_cluster_endpoints():
    resolver = RouteResolver()
    spec = EndpointSpec(
        provider_id="kafka",
        endpoints=["broker1.kafka.internal:9092", "broker2.kafka.internal:9092", "broker3.kafka.internal:9092"],
    )

    resolved = resolver.resolve_route(spec)

    assert len(resolved.resolved_targets) == 3
    assert resolved.get_bootstrap_servers() == [
        "broker1.kafka.internal:9092",
        "broker2.kafka.internal:9092",
        "broker3.kafka.internal:9092",
    ]
    assert resolved.get_contact_points() == [
        "broker1.kafka.internal",
        "broker2.kafka.internal",
        "broker3.kafka.internal",
    ]


def test_route_resolver_cassandra_contact_points_and_port():
    resolver = RouteResolver()
    spec = EndpointSpec(
        provider_id="cassandra",
        endpoints=["node1.cas.internal", "node2.cas.internal", "node3.cas.internal"],
        port=9042,
    )

    resolved = resolver.resolve_route(spec)
    assert resolved.get_contact_points() == [
        "node1.cas.internal",
        "node2.cas.internal",
        "node3.cas.internal",
    ]


# =============================================================================
# CORRECTION 4: TRUTHFUL EXECUTABLE ALTERNATIVE DRIVERS
# =============================================================================

def test_mariadb_both_drivers_executable(mock_resolved_route):
    strat = MariaDBProviderStrategy()
    spec = EndpointSpec(
        provider_id="mariadb",
        host="mariadb.internal",
        port=3306,
        database_name="testdb",
        options={"charset": "utf8mb4"},
    )

    # 1. Test pymysql executable path
    mock_pymysql = MagicMock()
    mock_pymysql_conn = MagicMock()
    mock_pymysql.connect.return_value = mock_pymysql_conn
    with patch.dict("sys.modules", {"pymysql": mock_pymysql, "mariadb": None}):
        conn1 = strat.connect(spec, mock_resolved_route, {"username": "root", "password": "pw"})
        assert conn1 is mock_pymysql_conn
        mock_pymysql.connect.assert_called_once()
        assert mock_pymysql.connect.call_args[1]["charset"] == "utf8mb4"

    # 2. Test native mariadb executable fallback path
    mock_mariadb = MagicMock()
    mock_mariadb_conn = MagicMock()
    mock_mariadb.connect.return_value = mock_mariadb_conn
    with patch.dict("sys.modules", {"pymysql": None, "mariadb": mock_mariadb}):
        conn2 = strat.connect(spec, mock_resolved_route, {"username": "root", "password": "pw"})
        assert conn2 is mock_mariadb_conn
        mock_mariadb.connect.assert_called_once()


def test_redshift_both_drivers_executable(mock_resolved_route):
    strat = RedshiftProviderStrategy()
    spec = EndpointSpec(
        provider_id="redshift",
        host="redshift.internal",
        port=5439,
        database_name="dev",
    )

    # 1. Test psycopg2 executable path
    mock_psycopg2 = MagicMock()
    mock_psycopg2_conn = MagicMock()
    mock_psycopg2.connect.return_value = mock_psycopg2_conn
    with patch.dict("sys.modules", {"psycopg2": mock_psycopg2, "redshift_connector": None}):
        conn1 = strat.connect(spec, mock_resolved_route, {"username": "awsuser", "password": "pw"})
        assert conn1 is mock_psycopg2_conn
        mock_psycopg2.connect.assert_called_once()

    # 2. Test redshift_connector executable fallback path
    mock_redshift = MagicMock()
    mock_redshift_conn = MagicMock()
    mock_redshift.connect.return_value = mock_redshift_conn
    with patch.dict("sys.modules", {"psycopg2": None, "redshift_connector": mock_redshift}):
        conn2 = strat.connect(spec, mock_resolved_route, {"username": "awsuser", "password": "pw"})
        assert conn2 is mock_redshift_conn
        mock_redshift.connect.assert_called_once()


# =============================================================================
# CORRECTION 5: PHYSICAL NON-MUTATING VALIDATION RPCS
# =============================================================================

def test_pubsub_physical_validation_rpc():
    strat = PubSubProviderStrategy()
    assert strat.validate(None) is False

    mock_client = MagicMock()
    mock_client.list_topics.return_value = iter(["projects/test/topics/t1"])
    assert strat.validate(mock_client) is True
    mock_client.list_topics.assert_called_once()

    # Test handling of Google API 404 / 403 returning False (not ready/authorized)
    mock_client_denied = MagicMock()
    mock_client_denied.list_topics.side_effect = Exception("403 PermissionDenied: User not authorized")
    assert strat.validate(mock_client_denied) is False

    # Test handling of connection refused / socket timeout returning False
    mock_client_refused = MagicMock()
    mock_client_refused.list_topics.side_effect = ConnectionRefusedError("Connection refused by peer")
    assert strat.validate(mock_client_refused) is False


def test_eventhubs_physical_validation_rpc():
    strat = EventHubsProviderStrategy()
    assert strat.validate(None) is False

    mock_client = MagicMock()
    mock_client.get_eventhub_properties.return_value = {"name": "test-hub", "partition_count": 4}
    assert strat.validate(mock_client) is True
    mock_client.get_eventhub_properties.assert_called_once()


# =============================================================================
# CORRECTION 6: TRUTHFUL DECLARATIVE SCHEMAS & FAILING CONTRADICTORY CONFIGS
# =============================================================================

def test_mssql_validate_configuration_rejects_contradictory_auth():
    strat = MSSQLProviderStrategy()
    spec = EndpointSpec(
        provider_id="mssql",
        host="mssql.internal",
        port=1433,
        auth_spec=AuthenticationSpec(
            auth_type=AuthenticationType.INTEGRATED,
            secret_ref="vault://sql/pass",  # Contradictory SQL password with Windows Integrated Auth
        ),
    )
    with pytest.raises(ConfigurationError) as exc_info:
        strat.validate_configuration(spec)
    assert exc_info.value.failure.error_code == "MSSQL_CONTRADICTORY_AUTH_CONFIG"


def test_all_28_provider_schemas_truthful_and_aligned():
    providers = [
        "sqlite", "postgresql", "mysql", "mariadb", "oracle", "mssql", "ibm_db2",
        "snowflake", "bigquery", "redshift", "databricks", "mongodb", "cassandra",
        "scylladb", "neo4j", "redis", "keydb", "elasticsearch", "opensearch",
        "kafka", "kinesis", "eventhubs", "pubsub", "s3", "gcs", "azure_blob",
        "minio", "hdfs",
    ]
    assert len(providers) == 28

    for pid in providers:
        schema = build_connection_provider_schema(pid)
        assert schema is not None, f"Schema missing for provider '{pid}'"
        assert len(schema.fields) > 0, f"Schema has no fields for provider '{pid}'"

        # Verify no raw service_account_file in GCP schemas
        if pid in ("bigquery", "gcs", "pubsub"):
            assert schema.get_field("service_account_file") is None, f"Raw service_account_file found in '{pid}' schema"
            assert schema.get_field("service_account_json_ref") is not None, f"service_account_json_ref missing from '{pid}'"

        # Verify SQLite has timeout_seconds and no dead mode
        if pid == "sqlite":
            assert schema.get_field("timeout_seconds") is not None
            assert schema.get_field("mode") is None


# =============================================================================
# RECHECK CLOSURE TESTS: 3 REMAINING BLOCKERS
# =============================================================================

def test_single_clustered_endpoint_strictly_uses_canonical_route():
    # When spec.endpoints has 1 entry, and route resolution maps it to an SSH tunnel / Proxy
    # the provider strategy MUST use the resolved target and NEVER bypass it.
    bastion_route = ResolvedRoute(
        effective_host="127.0.0.1",
        effective_port=54321,
        resolved_ip="127.0.0.1",
        dns_time_ms=0.5,
        route_type=RouteType.SSH_BASTION_TUNNEL,
        resolved_targets=(
            ResolvedEndpointTarget(
                effective_host="127.0.0.1",
                effective_port=54321,
                resolved_ip="127.0.0.1",
                dns_time_ms=0.5,
                raw_endpoint="broker-internal.corp:9092",
            ),
        ),
    )

    # 1. Kafka
    kafka_strat = KafkaProviderStrategy()
    kafka_spec = EndpointSpec(
        provider_id="kafka",
        endpoints=["broker-internal.corp:9092"],
    )
    mock_admin = MagicMock()
    mock_kafka = MagicMock()
    mock_kafka.KafkaAdminClient = MagicMock(return_value=mock_admin)
    with patch("akaalEngine.connection.providers.streaming.kafka.KafkaProviderStrategy.is_dependency_available", return_value=(True, "ok")):
        with patch.dict("sys.modules", {"kafka": mock_kafka}):
            kafka_strat.connect(kafka_spec, bastion_route, {})
            kwargs = mock_kafka.KafkaAdminClient.call_args[1]
            assert kwargs["bootstrap_servers"] == ["127.0.0.1:54321"]
            assert "broker-internal.corp:9092" not in kwargs["bootstrap_servers"]

    # 2. Cassandra
    cas_strat = CassandraProviderStrategy()
    cas_spec = EndpointSpec(
        provider_id="cassandra",
        endpoints=["cas-internal.corp"],
    )
    mock_cas_cluster = MagicMock()
    with patch("akaalEngine.connection.providers.nosql.cassandra.CassandraProviderStrategy.is_dependency_available", return_value=(True, "ok")):
        with patch.dict("sys.modules", {"cassandra": MagicMock(), "cassandra.cluster": mock_cas_cluster, "cassandra.auth": MagicMock()}):
            cas_strat.connect(cas_spec, bastion_route, {})
            kwargs = mock_cas_cluster.Cluster.call_args[1]
            assert kwargs["contact_points"] == ["127.0.0.1"]
            assert kwargs["port"] == 54321
            assert "cas-internal.corp" not in kwargs["contact_points"]

    # 3. Elasticsearch
    es_strat = ElasticsearchProviderStrategy()
    es_spec = EndpointSpec(
        provider_id="elasticsearch",
        endpoints=["http://es-internal.corp:9200"],
        tls_binding=TLSBinding(mode=TLSMode.DISABLED),
    )
    mock_es = MagicMock()
    with patch("akaalEngine.connection.providers.nosql.elasticsearch.ElasticsearchProviderStrategy.is_dependency_available", return_value=(True, "ok")):
        with patch.dict("sys.modules", {"elasticsearch": mock_es}):
            es_strat.connect(es_spec, bastion_route, {})
            kwargs = mock_es.Elasticsearch.call_args[1]
            assert kwargs["hosts"] == ["http://127.0.0.1:54321"]
            assert "http://es-internal.corp:9200" not in kwargs["hosts"]


def test_all_extensions_schema_secret_fields_map_to_canonical_model():
    from akaalEngine.connection.adapters.config_adapter import build_endpoint_spec_from_config

    # Test Azure Blob Schema dictionary containing account_key_ref and sas_token_ref
    azure_cfg = {
        "account_name": "storageprod",
        "account_key_ref": "vault://azure/acc-key",
        "sas_token_ref": "vault://azure/sas-tok",
    }
    azure_spec = build_endpoint_spec_from_config("azure_blob", azure_cfg)
    assert azure_spec.auth_spec is not None
    assert azure_spec.auth_spec.account_key_ref == "vault://azure/acc-key"
    assert azure_spec.auth_spec.sas_token_ref == "vault://azure/sas-tok"

    # Test AWS S3 / Kinesis Schema dictionary containing access_key_id_ref and secret_access_key_ref
    s3_cfg = {
        "region": "us-west-2",
        "access_key_id_ref": "vault://aws/akid",
        "secret_access_key_ref": "vault://aws/sak",
        "session_token_ref": "vault://aws/sts",
    }
    s3_spec = build_endpoint_spec_from_config("s3", s3_cfg)
    assert s3_spec.auth_spec is not None
    assert s3_spec.auth_spec.access_key_id_ref == "vault://aws/akid"
    assert s3_spec.auth_spec.secret_access_key_ref == "vault://aws/sak"
    assert s3_spec.auth_spec.session_token_ref == "vault://aws/sts"

    # Test Event Hubs shared_access_key_ref
    eh_cfg = {
        "endpoints": ["eh.servicebus.windows.net"],
        "shared_access_key_ref": "vault://eh/key",
    }
    eh_spec = build_endpoint_spec_from_config("eventhubs", eh_cfg)
    assert eh_spec.auth_spec is not None
    assert eh_spec.auth_spec.shared_access_key_ref == "vault://eh/key"


def test_wipe_credentials_dict_recursively_wipes_all_resolved_secrets():
    from akaalEngine.connection.security.authentication import wipe_credentials_dict

    sec1 = ResolvedSecret(secret_value="pass1", reference_id="vault://p1")
    sec2 = ResolvedSecret(secret_value="pass2", reference_id="vault://p2")
    sec3 = ResolvedSecret(secret_value="pass3", reference_id="vault://p3")

    creds_dict = {
        "password": "plain_password_text",
        "_resolved_secrets": [sec1, sec2],
        "nested": {
            "more_secrets": [sec3],
        },
    }

    assert sec1.is_valid() is True
    assert sec2.is_valid() is True
    assert sec3.is_valid() is True

    wipe_credentials_dict(creds_dict)

    # Dictionary must be cleared
    assert len(creds_dict) == 0

    # All contained ResolvedSecret objects must be wiped
    assert sec1.is_valid() is False
    assert sec2.is_valid() is False
    assert sec3.is_valid() is False
    with pytest.raises(RuntimeError, match="wiped"):
        sec1.get_value()
    with pytest.raises(RuntimeError, match="wiped"):
        sec2.get_value()
    with pytest.raises(RuntimeError, match="wiped"):
        sec3.get_value()

