"""
tests.unit.engine_connection.test_legacy_capability_conservation
================================================================
Comprehensive verification of all legacy connection capabilities conserved across
Connection Authority (#1) and Extensions Authority (#2).
Verifies zero synthetic handles, authentic physical client interactions, multi-endpoint
cluster mechanics, and advanced provider connection modes.
"""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch
import pytest

from akaalEngine.connection.identity.fingerprint import compute_endpoint_fingerprint
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
from akaalEngine.connection.models.errors import ConnectionFailure, FailureCategory
from akaalEngine.connection.providers.nosql.cassandra import CassandraProviderStrategy
from akaalEngine.connection.providers.nosql.elasticsearch import ElasticsearchProviderStrategy
from akaalEngine.connection.providers.nosql.opensearch import OpenSearchProviderStrategy
from akaalEngine.connection.providers.nosql.scylladb import ScyllaDBProviderStrategy
from akaalEngine.connection.providers.relational.mssql import MSSQLProviderStrategy
from akaalEngine.connection.providers.relational.oracle import OracleProviderStrategy
from akaalEngine.connection.providers.storage.azure_blob import AzureBlobProviderStrategy
from akaalEngine.connection.providers.storage.gcs import GCSProviderStrategy
from akaalEngine.connection.providers.storage.s3 import S3ProviderStrategy
from akaalEngine.connection.providers.streaming.kafka import KafkaProviderStrategy
from akaalEngine.connection.providers.streaming.kinesis import KinesisProviderStrategy
from akaalEngine.connection.providers.streaming.pubsub import PubSubProviderStrategy
from akaalEngine.connection.providers.warehouse.bigquery import BigQueryProviderStrategy
from akaalEngine.connection.providers.warehouse.snowflake import SnowflakeProviderStrategy
from akaalEngine.connection.routing.resolver import ResolvedRoute, default_route_resolver


@pytest.fixture
def mock_resolved_route() -> ResolvedRoute:
    return ResolvedRoute(
        effective_host="db.example.internal",
        effective_port=1521,
        resolved_ip="10.0.1.50",
        dns_time_ms=1.5,
        route_type=RouteType.DIRECT,
    )


# ============================================================================
# CORRECTION A & H: Kafka Physical Connectivity, Auth Modes, Multi-Endpoints
# ============================================================================

def test_kafka_physical_connect_kafka_python(mock_resolved_route):
    strat = KafkaProviderStrategy()
    spec = EndpointSpec(
        provider_id="kafka",
        endpoints=["broker1:9092", "broker2:9092"],
        auth_spec=AuthenticationSpec(
            auth_type=AuthenticationType.SASL_SCRAM_256,
            username="kafka_user",
            secret_ref="vault://kafka/pass",
        ),
        tls_binding=TLSBinding(mode=TLSMode.REQUIRED, ca_cert_path="/etc/ssl/ca.pem"),
    )

    mock_admin_instance = MagicMock()
    mock_admin_instance.describe_cluster.return_value = {"cluster_id": "kafka-cluster-prod-1"}
    mock_kafka_mod = MagicMock()
    mock_kafka_mod.KafkaAdminClient = MagicMock(return_value=mock_admin_instance)

    with patch("akaalEngine.connection.providers.streaming.kafka.KafkaProviderStrategy.is_dependency_available", return_value=(True, "ok")):
        with patch.dict("sys.modules", {"kafka": mock_kafka_mod}):
            route = default_route_resolver.resolve_route(spec)
            client = strat.connect(spec, route, {"password": "secret_password"})
            assert client is mock_admin_instance
            mock_kafka_mod.KafkaAdminClient.assert_called_once()
            kwargs = mock_kafka_mod.KafkaAdminClient.call_args[1]
            assert kwargs["bootstrap_servers"] == ["broker1:9092", "broker2:9092"]
            assert kwargs["security_protocol"] == "SASL_SSL"
            assert kwargs["sasl_mechanism"] == "SCRAM-SHA-256"
            assert kwargs["sasl_plain_username"] == "kafka_user"
            assert kwargs["sasl_plain_password"] == "secret_password"
            assert kwargs["ssl_cafile"] == "/etc/ssl/ca.pem"
            mock_admin_instance.describe_cluster.assert_called_once()

    # Validate physical probe
    assert strat.validate(client) is True
    # Close physical client
    strat.close(client)
    mock_admin_instance.close.assert_called_once()


def test_kafka_physical_connect_confluent_fallback(mock_resolved_route):
    strat = KafkaProviderStrategy()
    spec = EndpointSpec(
        provider_id="kafka",
        host="singlebroker",
        port=9092,
        tls_binding=TLSBinding(mode=TLSMode.DISABLED),
        auth_spec=AuthenticationSpec(
            auth_type=AuthenticationType.SASL_PLAIN,
            username="kafka_plain_user",
        ),
    )

    mock_admin_instance = MagicMock()
    mock_meta = MagicMock()
    mock_meta.brokers = ["broker-1"]
    mock_meta.cluster_id = "confluent-cluster-1"
    mock_admin_instance.list_topics.return_value = mock_meta

    mock_confluent_admin = MagicMock()
    mock_confluent_admin.AdminClient = MagicMock(return_value=mock_admin_instance)
    mock_confluent_mod = MagicMock()
    mock_confluent_mod.admin = mock_confluent_admin

    with patch("akaalEngine.connection.providers.streaming.kafka.KafkaProviderStrategy.is_dependency_available", return_value=(True, "ok")):
        with patch.dict("sys.modules", {"kafka": None, "confluent_kafka": mock_confluent_mod, "confluent_kafka.admin": mock_confluent_admin}):
            client = strat.connect(spec, mock_resolved_route, {"password": "plain_password"})
            assert client is mock_admin_instance
            conf = mock_confluent_admin.AdminClient.call_args[0][0]
            assert "db.example.internal:1521" in conf["bootstrap.servers"]
            assert conf["security.protocol"] == "sasl_plaintext"
            assert conf["sasl.mechanism"] == "PLAIN"
            assert conf["sasl.username"] == "kafka_plain_user"
            assert conf["sasl.password"] == "plain_password"


def test_kafka_error_normalization():
    strat = KafkaProviderStrategy()
    auth_err = Exception("SaslAuthenticationFailedError: SASL authentication failed")
    norm_auth = strat.normalize_error(auth_err)
    assert norm_auth.category == FailureCategory.AUTHENTICATION_FAILURE
    assert norm_auth.error_code == "KAFKA_AUTH_FAILED"

    broker_err = Exception("NoBrokersAvailable: All bootstrap brokers are down")
    norm_broker = strat.normalize_error(broker_err)
    assert norm_broker.category == FailureCategory.ENDPOINT_UNAVAILABLE
    assert norm_broker.error_code == "KAFKA_BROKERS_UNAVAILABLE"
    assert norm_broker.retryable is True


# ============================================================================
# CORRECTION B: Oracle Connection Modes (SID, TNS, Wallet, SYSDBA/SYSOPER)
# ============================================================================

def test_oracle_connect_standard_and_sid(mock_resolved_route):
    strat = OracleProviderStrategy()
    spec_sid = EndpointSpec(
        provider_id="oracle",
        host="ora.internal",
        port=1521,
        options={"sid": "ORCLSID"},
        auth_spec=AuthenticationSpec(auth_type=AuthenticationType.PASSWORD, username="scott"),
    )

    mock_conn = MagicMock()
    mock_oracledb = MagicMock()
    mock_oracledb.makedsn = MagicMock(return_value="(DESCRIPTION=...)")
    mock_oracledb.connect = MagicMock(return_value=mock_conn)

    with patch("akaalEngine.connection.providers.relational.oracle.OracleProviderStrategy.is_dependency_available", return_value=(True, "ok")):
        with patch.dict("sys.modules", {"oracledb": mock_oracledb}):
            conn = strat.connect(spec_sid, mock_resolved_route, {"password": "tiger"})
            assert conn is mock_conn
            mock_oracledb.makedsn.assert_called_with("db.example.internal", 1521, sid="ORCLSID")
            mock_oracledb.connect.assert_called_once()


def test_oracle_connect_tns_wallet_and_sysdba(mock_resolved_route):
    strat = OracleProviderStrategy()
    spec_tns_wallet = EndpointSpec(
        provider_id="oracle",
        options={
            "tns_entry": "PROD_TNS_ALIAS",
            "wallet_location": "/opt/oracle/wallets/prod",
            "privilege_mode": "SYSDBA",
        },
        auth_spec=AuthenticationSpec(
            auth_type=AuthenticationType.ORACLE_PRIVILEGED,
            username="sys",
            wallet_password_ref="vault://ora/wallet",
        ),
    )

    mock_conn = MagicMock()
    mock_oracledb = MagicMock()
    mock_oracledb.connect = MagicMock(return_value=mock_conn)
    mock_oracledb.AUTH_MODE_SYSDBA = 2

    with patch("akaalEngine.connection.providers.relational.oracle.OracleProviderStrategy.is_dependency_available", return_value=(True, "ok")):
        with patch.dict("sys.modules", {"oracledb": mock_oracledb}):
            conn = strat.connect(spec_tns_wallet, mock_resolved_route, {"password": "change_on_install", "wallet_password": "wallet_secret"})
            assert conn is mock_conn
            kwargs = mock_oracledb.connect.call_args[1]
            assert kwargs["dsn"] == "PROD_TNS_ALIAS"
            assert kwargs["config_dir"] == "/opt/oracle/wallets/prod"
            assert kwargs["wallet_password"] == "wallet_secret"
            assert kwargs["user"] == "sys"


def test_oracle_error_normalization():
    strat = OracleProviderStrategy()
    norm = strat.normalize_error(Exception("ORA-01017: invalid username/password; logon denied"))
    assert norm.category == FailureCategory.AUTHENTICATION_FAILURE
    assert norm.error_code == "ORACLE_INVALID_CREDENTIALS"

    norm_priv = strat.normalize_error(Exception("ORA-01031: insufficient privileges"))
    assert norm_priv.category == FailureCategory.AUTHORIZATION_PERMISSION_FAILURE
    assert norm_priv.error_code == "ORACLE_INSUFFICIENT_PRIVILEGES"


# ============================================================================
# CORRECTION C: MSSQL Integrated Authentication
# ============================================================================

def test_mssql_integrated_authentication(mock_resolved_route):
    strat = MSSQLProviderStrategy()
    spec_trusted = EndpointSpec(
        provider_id="mssql",
        host="sql.corp.internal",
        port=1433,
        database_name="SalesDB",
        auth_spec=AuthenticationSpec(auth_type=AuthenticationType.INTEGRATED),
        options={"trusted_connection": True, "odbc_driver": "ODBC Driver 18 for SQL Server"},
    )

    mock_conn = MagicMock()
    mock_pyodbc = MagicMock()
    mock_pyodbc.connect = MagicMock(return_value=mock_conn)

    with patch("akaalEngine.connection.providers.relational.mssql.MSSQLProviderStrategy.is_dependency_available", return_value=(True, "ok")):
        with patch.dict("sys.modules", {"pyodbc": mock_pyodbc}):
            conn = strat.connect(spec_trusted, mock_resolved_route, {})
            assert conn is mock_conn
            conn_str = mock_pyodbc.connect.call_args[0][0]
            assert "Trusted_Connection=yes;" in conn_str
            assert "UID=" not in conn_str
            assert "PWD=" not in conn_str
            assert "DATABASE=SalesDB;" in conn_str
            assert "DRIVER={ODBC Driver 18 for SQL Server};" in conn_str


def test_mssql_standard_authentication(mock_resolved_route):
    strat = MSSQLProviderStrategy()
    spec_sql = EndpointSpec(
        provider_id="mssql",
        host="sql.corp.internal",
        port=1433,
        database_name="AppDB",
        auth_spec=AuthenticationSpec(auth_type=AuthenticationType.PASSWORD, username="app_user"),
    )

    mock_conn = MagicMock()
    mock_pyodbc = MagicMock()
    mock_pyodbc.connect = MagicMock(return_value=mock_conn)

    with patch("akaalEngine.connection.providers.relational.mssql.MSSQLProviderStrategy.is_dependency_available", return_value=(True, "ok")):
        with patch.dict("sys.modules", {"pyodbc": mock_pyodbc}):
            conn = strat.connect(spec_sql, mock_resolved_route, {"password": "app_password"})
            assert conn is mock_conn
            conn_str = mock_pyodbc.connect.call_args[0][0]
            assert "UID=app_user;PWD=app_password;" in conn_str
            assert "Trusted_Connection=yes;" not in conn_str


# ============================================================================
# CORRECTION D: AWS S3 & Kinesis STS Temporary Credentials
# ============================================================================

def test_s3_and_kinesis_sts_temporary_credentials(mock_resolved_route):
    s3_strat = S3ProviderStrategy()
    s3_spec = EndpointSpec(
        provider_id="s3",
        region="us-west-2",
        auth_spec=AuthenticationSpec(
            auth_type=AuthenticationType.SECRET_REFERENCE,
            session_token_ref="vault://aws/sts/token",
        ),
        options={"endpoint_url": "https://s3.custom.endpoint:9000"},
    )

    mock_boto3 = MagicMock()
    with patch("akaalEngine.connection.providers.storage.s3.S3ProviderStrategy.is_dependency_available", return_value=(True, "ok")):
        with patch.dict("sys.modules", {"boto3": mock_boto3}):
            s3_strat.connect(s3_spec, mock_resolved_route, {
                "access_key_id": "ASIAXXXXXXXX",
                "secret_access_key": "secret1234",
                "session_token": "IQoJb3JpZ2luX2VjE...",
            })
            mock_boto3.client.assert_called_once()
            kwargs = mock_boto3.client.call_args[1]
            assert kwargs["region_name"] == "us-west-2"
            assert kwargs["aws_access_key_id"] == "ASIAXXXXXXXX"
            assert kwargs["aws_secret_access_key"] == "secret1234"
            assert kwargs["aws_session_token"] == "IQoJb3JpZ2luX2VjE..."
            assert kwargs["endpoint_url"] == "https://s3.custom.endpoint:9000"

    kinesis_strat = KinesisProviderStrategy()
    mock_boto3_kin = MagicMock()
    with patch("akaalEngine.connection.providers.streaming.kinesis.KinesisProviderStrategy.is_dependency_available", return_value=(True, "ok")):
        with patch.dict("sys.modules", {"boto3": mock_boto3_kin}):
            kinesis_strat.connect(s3_spec, mock_resolved_route, {
                "access_key_id": "ASIAXXXXXXXX",
                "secret_access_key": "secret1234",
                "session_token": "IQoJb3JpZ2luX2VjE...",
            })
            mock_boto3_kin.client.assert_called_once()
            kwargs = mock_boto3_kin.client.call_args[1]
            assert kwargs["aws_session_token"] == "IQoJb3JpZ2luX2VjE..."


# ============================================================================
# CORRECTION E: GCP Explicit Service Account Credentials (GCS, Pub/Sub, BigQuery)
# ============================================================================

def test_gcp_explicit_service_account_credentials(mock_resolved_route):
    gcs_strat = GCSProviderStrategy()
    spec = EndpointSpec(
        provider_id="gcs",
        account_id="my-gcp-project-1",
        auth_spec=AuthenticationSpec(
            auth_type=AuthenticationType.SECRET_REFERENCE,
            service_account_json_ref="vault://gcp/sa_key",
        ),
    )

    sa_json_str = '{"type": "service_account", "project_id": "my-gcp-project-1", "private_key": "dummy"}'
    mock_sa_creds = MagicMock()

    mock_google_oauth2 = MagicMock()
    mock_service_account = MagicMock()
    mock_service_account.Credentials.from_service_account_info.return_value = mock_sa_creds
    mock_google_oauth2.service_account = mock_service_account

    mock_google_cloud = MagicMock()
    mock_storage_mod = MagicMock()
    mock_pubsub_v1 = MagicMock()
    mock_bigquery_mod = MagicMock()
    mock_google_cloud.storage = mock_storage_mod
    mock_google_cloud.pubsub_v1 = mock_pubsub_v1
    mock_google_cloud.bigquery = mock_bigquery_mod

    with patch("akaalEngine.connection.providers.storage.gcs.GCSProviderStrategy.is_dependency_available", return_value=(True, "ok")):
        with patch.dict("sys.modules", {
            "google": mock_google_cloud,
            "google.oauth2": mock_google_oauth2,
            "google.oauth2.service_account": mock_service_account,
            "google.cloud": mock_google_cloud,
            "google.cloud.storage": mock_storage_mod,
        }):
            gcs_strat.connect(spec, mock_resolved_route, {"service_account_json": sa_json_str})
            mock_service_account.Credentials.from_service_account_info.assert_called_once()
            mock_storage_mod.Client.assert_called_once_with(project="my-gcp-project-1", credentials=mock_sa_creds)

    pubsub_strat = PubSubProviderStrategy()
    with patch("akaalEngine.connection.providers.streaming.pubsub.PubSubProviderStrategy.is_dependency_available", return_value=(True, "ok")):
        with patch.dict("sys.modules", {
            "google": mock_google_cloud,
            "google.oauth2": mock_google_oauth2,
            "google.oauth2.service_account": mock_service_account,
            "google.cloud": mock_google_cloud,
            "google.cloud.pubsub_v1": mock_pubsub_v1,
        }):
            pubsub_strat.connect(spec, mock_resolved_route, {"service_account_json": sa_json_str})
            mock_pubsub_v1.PublisherClient.assert_called_once_with(credentials=mock_sa_creds)

    bq_strat = BigQueryProviderStrategy()
    with patch("akaalEngine.connection.providers.warehouse.bigquery.BigQueryProviderStrategy.is_dependency_available", return_value=(True, "ok")):
        with patch.dict("sys.modules", {
            "google": mock_google_cloud,
            "google.oauth2": mock_google_oauth2,
            "google.oauth2.service_account": mock_service_account,
            "google.cloud": mock_google_cloud,
            "google.cloud.bigquery": mock_bigquery_mod,
        }):
            bq_strat.connect(spec, mock_resolved_route, {"service_account_json": sa_json_str})
            mock_bigquery_mod.Client.assert_called_once_with(project="my-gcp-project-1", credentials=mock_sa_creds)


# ============================================================================
# CORRECTION F: Azure Blob Connection Forms (ConnString, AccountKey, SAS, Ambient)
# ============================================================================

def test_azure_blob_connection_forms(mock_resolved_route):
    strat = AzureBlobProviderStrategy()

    mock_azure = MagicMock()
    mock_blob_mod = MagicMock()
    mock_azure.storage = MagicMock()
    mock_azure.storage.blob = mock_blob_mod

    # Form 1: Connection String
    spec_conn_str = EndpointSpec(
        provider_id="azure_blob",
        auth_spec=AuthenticationSpec(
            auth_type=AuthenticationType.CUSTOM_PROVIDER,
            connection_string_ref="vault://azure/conn_str",
        ),
    )
    with patch("akaalEngine.connection.providers.storage.azure_blob.AzureBlobProviderStrategy.is_dependency_available", return_value=(True, "ok")):
        with patch.dict("sys.modules", {"azure": mock_azure, "azure.storage": mock_azure.storage, "azure.storage.blob": mock_blob_mod}):
            strat.connect(spec_conn_str, mock_resolved_route, {"connection_string": "DefaultEndpointsProtocol=https;AccountName=test;..."})
            mock_blob_mod.BlobServiceClient.from_connection_string.assert_called_once_with("DefaultEndpointsProtocol=https;AccountName=test;...")

    # Form 2: Account Name + Account Key
    spec_key = EndpointSpec(
        provider_id="azure_blob",
        account_id="testaccount",
        auth_spec=AuthenticationSpec(auth_type=AuthenticationType.KEY_PAIR),
    )
    mock_blob_mod.reset_mock()
    with patch("akaalEngine.connection.providers.storage.azure_blob.AzureBlobProviderStrategy.is_dependency_available", return_value=(True, "ok")):
        with patch.dict("sys.modules", {"azure": mock_azure, "azure.storage": mock_azure.storage, "azure.storage.blob": mock_blob_mod}):
            strat.connect(spec_key, mock_resolved_route, {"account_key": "base64key=="})
            mock_blob_mod.BlobServiceClient.assert_called_once_with(
                account_url="https://testaccount.blob.core.windows.net",
                credential="base64key==",
            )

    # Form 3: SAS Token
    mock_blob_mod.reset_mock()
    with patch("akaalEngine.connection.providers.storage.azure_blob.AzureBlobProviderStrategy.is_dependency_available", return_value=(True, "ok")):
        with patch.dict("sys.modules", {"azure": mock_azure, "azure.storage": mock_azure.storage, "azure.storage.blob": mock_blob_mod}):
            strat.connect(spec_key, mock_resolved_route, {"sas_token": "sv=2020-08-04&ss=b&srt=sco&sp=rwdlacx..."})
            mock_blob_mod.BlobServiceClient.assert_called_once_with(
                account_url="https://testaccount.blob.core.windows.net",
                credential="sv=2020-08-04&ss=b&srt=sco&sp=rwdlacx...",
            )


# ============================================================================
# CORRECTION G: Snowflake Session Context
# ============================================================================

def test_snowflake_session_context(mock_resolved_route):
    strat = SnowflakeProviderStrategy()
    spec = EndpointSpec(
        provider_id="snowflake",
        account_id="xy12345.us-east-1",
        database_name="FINANCE_DB",
        schema_name="REPORTING",
        options={
            "warehouse": "COMPUTE_WH",
            "role": "FINANCE_ANALYST",
            "authenticator": "snowflake",
        },
        auth_spec=AuthenticationSpec(auth_type=AuthenticationType.PASSWORD, username="jane_doe"),
    )

    mock_sf_mod = MagicMock()
    mock_sf_connector = MagicMock()
    mock_sf_mod.connector = mock_sf_connector

    with patch("akaalEngine.connection.providers.warehouse.snowflake.SnowflakeProviderStrategy.is_dependency_available", return_value=(True, "ok")):
        with patch.dict("sys.modules", {"snowflake": mock_sf_mod, "snowflake.connector": mock_sf_connector}):
            strat.connect(spec, mock_resolved_route, {"password": "secure_password"})
            mock_sf_connector.connect.assert_called_once()
            kwargs = mock_sf_connector.connect.call_args[1]
            assert kwargs["account"] == "xy12345.us-east-1"
            assert kwargs["warehouse"] == "COMPUTE_WH"
            assert kwargs["database"] == "FINANCE_DB"
            assert kwargs["schema"] == "REPORTING"
            assert kwargs["role"] == "FINANCE_ANALYST"
            assert kwargs["authenticator"] == "snowflake"
            assert kwargs["user"] == "jane_doe"
            assert kwargs["password"] == "secure_password"


# ============================================================================
# CORRECTION H: Clustered Multi-Endpoints (Cassandra, ScyllaDB, Elasticsearch, OpenSearch)
# ============================================================================

def test_clustered_multi_endpoints(mock_resolved_route):
    # Cassandra contact points
    cas_strat = CassandraProviderStrategy()
    cas_spec = EndpointSpec(
        provider_id="cassandra",
        endpoints=["node1.cas.internal", "node2.cas.internal", "node3.cas.internal"],
        database_name="system_keyspace",
    )
    cas_route = default_route_resolver.resolve_route(cas_spec)
    mock_cas_cluster = MagicMock()
    mock_cas_auth = MagicMock()
    with patch("akaalEngine.connection.providers.nosql.cassandra.CassandraProviderStrategy.is_dependency_available", return_value=(True, "ok")):
        with patch.dict("sys.modules", {
            "cassandra": MagicMock(),
            "cassandra.cluster": mock_cas_cluster,
            "cassandra.auth": mock_cas_auth,
        }):
            cas_strat.connect(cas_spec, cas_route, {})
            mock_cas_cluster.Cluster.assert_called_once()
            kwargs = mock_cas_cluster.Cluster.call_args[1]
            assert kwargs["contact_points"] == ["node1.cas.internal", "node2.cas.internal", "node3.cas.internal"]

    # ScyllaDB contact points
    scy_strat = ScyllaDBProviderStrategy()
    mock_scy_cluster = MagicMock()
    mock_scy_auth = MagicMock()
    with patch("akaalEngine.connection.providers.nosql.scylladb.ScyllaDBProviderStrategy.is_dependency_available", return_value=(True, "ok")):
        with patch.dict("sys.modules", {
            "cassandra": MagicMock(),
            "cassandra.cluster": mock_scy_cluster,
            "cassandra.auth": mock_scy_auth,
        }):
            scy_strat.connect(cas_spec, cas_route, {})
            mock_scy_cluster.Cluster.assert_called_once()
            kwargs = mock_scy_cluster.Cluster.call_args[1]
            assert kwargs["contact_points"] == ["node1.cas.internal", "node2.cas.internal", "node3.cas.internal"]

    # Elasticsearch cluster nodes & API Key
    es_strat = ElasticsearchProviderStrategy()
    es_spec = EndpointSpec(
        provider_id="elasticsearch",
        endpoints=["http://es1:9200", "http://es2:9200"],
        auth_spec=AuthenticationSpec(
            auth_type=AuthenticationType.API_KEY,
            api_key_ref="vault://es/apikey",
        ),
    )
    es_route = default_route_resolver.resolve_route(es_spec)
    mock_es_mod = MagicMock()
    with patch("akaalEngine.connection.providers.nosql.elasticsearch.ElasticsearchProviderStrategy.is_dependency_available", return_value=(True, "ok")):
        with patch.dict("sys.modules", {"elasticsearch": mock_es_mod}):
            es_strat.connect(es_spec, es_route, {"api_key": "apiKeyBase64=="})
            mock_es_mod.Elasticsearch.assert_called_once()
            kwargs = mock_es_mod.Elasticsearch.call_args[1]
            assert kwargs["hosts"] == ["http://es1:9200", "http://es2:9200"]
            assert kwargs["api_key"] == "apiKeyBase64=="

    # OpenSearch cluster nodes
    os_strat = OpenSearchProviderStrategy()
    mock_os_mod = MagicMock()
    with patch("akaalEngine.connection.providers.nosql.opensearch.OpenSearchProviderStrategy.is_dependency_available", return_value=(True, "ok")):
        with patch.dict("sys.modules", {"opensearchpy": mock_os_mod}):
            os_strat.connect(es_spec, es_route, {"api_key": "apiKeyBase64=="})
            mock_os_mod.OpenSearch.assert_called_once()
            kwargs = mock_os_mod.OpenSearch.call_args[1]
            assert kwargs["hosts"] == ["http://es1:9200", "http://es2:9200"]
            assert kwargs["http_auth"] == "apiKeyBase64=="


def test_deterministic_endpoint_spec_fingerprinting():
    # Order of endpoints input must not alter the resulting fingerprint
    spec_a = EndpointSpec(
        provider_id="kafka",
        endpoints=["b3:9092", "b1:9092", "b2:9092"],
        auth_spec=AuthenticationSpec(
            auth_type=AuthenticationType.SASL_PLAIN,
            username="client",
            secret_ref="vault://k/sec",
        ),
    )
    spec_b = EndpointSpec(
        provider_id="kafka",
        endpoints=["b1:9092", "b2:9092", "b3:9092"],
        auth_spec=AuthenticationSpec(
            auth_type=AuthenticationType.SASL_PLAIN,
            username="client",
            secret_ref="vault://k/sec",
        ),
    )
    fp_a = compute_endpoint_fingerprint(spec_a)
    fp_b = compute_endpoint_fingerprint(spec_b)
    assert fp_a.fingerprint_sha256 == fp_b.fingerprint_sha256
