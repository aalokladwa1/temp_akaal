"""
akaalEngine.extensions.integration.builtin_connection_schemas
============================================================
Truthful declarative ConfigurationSchema descriptors for all 28 adopted physical database,
storage, warehouse, NoSQL, and streaming Connection providers.
Provides complete parameter descriptions, types, constraints, and secret references
for configuration validation, Gateway ingestion, and tooling introspection.
Guarantees zero dead fields and 100% alignment with physical Connection authority consumption.
"""

from __future__ import annotations

from typing import Optional

from akaalEngine.extensions.models.configuration import (
    ConfigurationCondition,
    ConfigurationConstraint,
    ConfigurationField,
    ConfigurationSchema,
)
from akaalEngine.extensions.models.enums import ConfigurationFieldType


def build_connection_provider_schema(provider_id_str: str) -> Optional[ConfigurationSchema]:
    """
    Returns the canonical ConfigurationSchema descriptor for the specified adopted Connection provider ID.
    Guarantees that all connection parameters, auth modes, and secret pointers are truthfully represented
    and physically consumed by the corresponding Connection ProviderStrategy.
    """
    pid = provider_id_str.strip().lower()

    if pid == "sqlite":
        return ConfigurationSchema(
            schema_id="sqlite-connection-config",
            schema_version="1.0.0",
            description="Configuration schema for SQLite database provider",
            fields=(
                ConfigurationField(
                    name="database_name",
                    field_type=ConfigurationFieldType.STRING,
                    description="File path to the SQLite database or ':memory:' for an in-memory database",
                    is_required=True,
                    default_value=":memory:",
                    ui_group="Target",
                ),
                ConfigurationField(
                    name="timeout_seconds",
                    field_type=ConfigurationFieldType.FLOAT,
                    description="Database lock timeout in seconds",
                    default_value=10.0,
                    ui_group="Connection",
                ),
            ),
        )

    elif pid == "postgresql":
        return ConfigurationSchema(
            schema_id="postgresql-connection-config",
            schema_version="1.0.0",
            description="Configuration schema for PostgreSQL database provider",
            fields=(
                ConfigurationField(name="host", field_type=ConfigurationFieldType.STRING, description="PostgreSQL server hostname or IP address", is_required=True, ui_group="Network"),
                ConfigurationField(name="port", field_type=ConfigurationFieldType.INTEGER, description="PostgreSQL server port", default_value=5432, constraint=ConfigurationConstraint(min_value=1, max_value=65535), ui_group="Network"),
                ConfigurationField(name="database_name", field_type=ConfigurationFieldType.STRING, description="Target database name", is_required=True, ui_group="Target"),
                ConfigurationField(name="schema_name", field_type=ConfigurationFieldType.STRING, description="Default schema search path", default_value="public", ui_group="Target"),
                ConfigurationField(name="username", field_type=ConfigurationFieldType.STRING, description="Database username", is_required=True, ui_group="Authentication"),
                ConfigurationField(name="password_ref", field_type=ConfigurationFieldType.SECRET_REF, description="Reference pointer to password secret", is_required=True, ui_group="Authentication"),
                ConfigurationField(name="connect_timeout", field_type=ConfigurationFieldType.INTEGER, description="TCP connect timeout in seconds", default_value=15, ui_group="Connection"),
            ),
        )

    elif pid in ("mysql", "mariadb"):
        return ConfigurationSchema(
            schema_id=f"{pid}-connection-config",
            schema_version="1.0.0",
            description=f"Configuration schema for {pid.upper()} database provider",
            fields=(
                ConfigurationField(name="host", field_type=ConfigurationFieldType.STRING, description=f"{pid.upper()} server hostname or IP address", is_required=True, ui_group="Network"),
                ConfigurationField(name="port", field_type=ConfigurationFieldType.INTEGER, description=f"{pid.upper()} server port", default_value=3306, constraint=ConfigurationConstraint(min_value=1, max_value=65535), ui_group="Network"),
                ConfigurationField(name="database_name", field_type=ConfigurationFieldType.STRING, description="Target database name", is_required=True, ui_group="Target"),
                ConfigurationField(name="username", field_type=ConfigurationFieldType.STRING, description="Database username", is_required=True, ui_group="Authentication"),
                ConfigurationField(name="password_ref", field_type=ConfigurationFieldType.SECRET_REF, description="Reference pointer to password secret", is_required=True, ui_group="Authentication"),
                ConfigurationField(name="charset", field_type=ConfigurationFieldType.STRING, description="Character set encoding", default_value="utf8mb4", ui_group="Connection"),
                ConfigurationField(name="connect_timeout", field_type=ConfigurationFieldType.INTEGER, description="TCP connect timeout in seconds", default_value=15, ui_group="Connection"),
            ),
        )

    elif pid == "oracle":
        return ConfigurationSchema(
            schema_id="oracle-connection-config",
            schema_version="1.0.0",
            description="Configuration schema for Oracle Database provider supporting Host/Port, SID, TNS, Wallet, and Privileged Modes",
            fields=(
                ConfigurationField(name="host", field_type=ConfigurationFieldType.STRING, description="Oracle server hostname or IP address (optional if tns_entry is set)", ui_group="Network"),
                ConfigurationField(name="port", field_type=ConfigurationFieldType.INTEGER, description="Oracle listener port", default_value=1521, constraint=ConfigurationConstraint(min_value=1, max_value=65535), ui_group="Network"),
                ConfigurationField(name="service_name", field_type=ConfigurationFieldType.STRING, description="Oracle Pluggable Database (PDB) or Service Name", default_value="ORCLPDB1", ui_group="Target"),
                ConfigurationField(name="sid", field_type=ConfigurationFieldType.STRING, description="Oracle System Identifier (SID) if connecting via SID rather than Service Name", ui_group="Target"),
                ConfigurationField(name="tns_entry", field_type=ConfigurationFieldType.STRING, description="TNS alias or descriptor defined in tnsnames.ora", ui_group="Target"),
                ConfigurationField(name="wallet_location", field_type=ConfigurationFieldType.STRING, description="Filesystem directory containing Oracle Wallet files (cwallet.sso/ewallet.p12)", ui_group="Security"),
                ConfigurationField(name="wallet_password_ref", field_type=ConfigurationFieldType.SECRET_REF, description="Reference pointer to Oracle Wallet password secret", ui_group="Security"),
                ConfigurationField(name="driver_mode", field_type=ConfigurationFieldType.STRING, description="python-oracledb execution mode", default_value="THIN", constraint=ConfigurationConstraint(allowed_values=("THIN", "THICK")), ui_group="Connection"),
                ConfigurationField(name="oracle_client_lib_dir", field_type=ConfigurationFieldType.STRING, description="Oracle Client library directory used only for explicit THICK mode", ui_group="Connection"),
                ConfigurationField(name="oracle_client_config_dir", field_type=ConfigurationFieldType.STRING, description="Oracle Client network configuration directory used only for explicit THICK initialization", ui_group="Connection"),
                ConfigurationField(name="username", field_type=ConfigurationFieldType.STRING, description="Oracle database username", is_required=True, ui_group="Authentication"),
                ConfigurationField(name="password_ref", field_type=ConfigurationFieldType.SECRET_REF, description="Reference pointer to Oracle password secret", ui_group="Authentication"),
                ConfigurationField(name="privilege_mode", field_type=ConfigurationFieldType.STRING, description="Privileged connection mode (NORMAL, SYSDBA, SYSOPER)", default_value="NORMAL", constraint=ConfigurationConstraint(allowed_values=("NORMAL", "SYSDBA", "SYSOPER")), ui_group="Authentication"),
            ),
        )

    elif pid == "mssql":
        return ConfigurationSchema(
            schema_id="mssql-connection-config",
            schema_version="1.0.0",
            description="Configuration schema for Microsoft SQL Server provider supporting SQL and Integrated Authentication",
            fields=(
                ConfigurationField(name="host", field_type=ConfigurationFieldType.STRING, description="SQL Server hostname or IP address", is_required=True, ui_group="Network"),
                ConfigurationField(name="port", field_type=ConfigurationFieldType.INTEGER, description="SQL Server port", default_value=1433, constraint=ConfigurationConstraint(min_value=1, max_value=65535), ui_group="Network"),
                ConfigurationField(name="database_name", field_type=ConfigurationFieldType.STRING, description="Target database name", default_value="master", ui_group="Target"),
                ConfigurationField(name="trusted_connection", field_type=ConfigurationFieldType.BOOLEAN, description="Enable Windows Integrated Authentication (SSPI / Trusted_Connection)", default_value=False, ui_group="Authentication"),
                ConfigurationField(name="integrated_security", field_type=ConfigurationFieldType.STRING, description="Integrated security provider (e.g. 'SSPI')", ui_group="Authentication"),
                ConfigurationField(name="username", field_type=ConfigurationFieldType.STRING, description="SQL Server login username (omitted when trusted_connection is enabled)", condition=ConfigurationCondition.when_field_equals("trusted_connection", False), ui_group="Authentication"),
                ConfigurationField(name="password_ref", field_type=ConfigurationFieldType.SECRET_REF, description="Reference pointer to password secret", condition=ConfigurationCondition.when_field_equals("trusted_connection", False), ui_group="Authentication"),
                ConfigurationField(name="odbc_driver", field_type=ConfigurationFieldType.STRING, description="ODBC driver name", default_value="ODBC Driver 17 for SQL Server", ui_group="Connection"),
            ),
        )

    elif pid == "ibm_db2":
        return ConfigurationSchema(
            schema_id="ibm-db2-connection-config",
            schema_version="1.0.0",
            description="Configuration schema for IBM DB2 provider",
            fields=(
                ConfigurationField(name="host", field_type=ConfigurationFieldType.STRING, description="IBM DB2 server hostname or IP address", is_required=True, ui_group="Network"),
                ConfigurationField(name="port", field_type=ConfigurationFieldType.INTEGER, description="IBM DB2 port", default_value=50000, constraint=ConfigurationConstraint(min_value=1, max_value=65535), ui_group="Network"),
                ConfigurationField(name="database_name", field_type=ConfigurationFieldType.STRING, description="Target database name", is_required=True, ui_group="Target"),
                ConfigurationField(name="schema_name", field_type=ConfigurationFieldType.STRING, description="Default schema name", ui_group="Target"),
                ConfigurationField(name="username", field_type=ConfigurationFieldType.STRING, description="DB2 user account", is_required=True, ui_group="Authentication"),
                ConfigurationField(name="password_ref", field_type=ConfigurationFieldType.SECRET_REF, description="Reference pointer to password secret", is_required=True, ui_group="Authentication"),
            ),
        )

    elif pid == "snowflake":
        return ConfigurationSchema(
            schema_id="snowflake-connection-config",
            schema_version="1.0.0",
            description="Configuration schema for Snowflake Cloud Data Warehouse provider",
            fields=(
                ConfigurationField(name="account", field_type=ConfigurationFieldType.STRING, description="Snowflake account locator/identifier", is_required=True, ui_group="Network"),
                ConfigurationField(name="warehouse", field_type=ConfigurationFieldType.STRING, description="Default virtual warehouse", ui_group="Target"),
                ConfigurationField(name="database_name", field_type=ConfigurationFieldType.STRING, description="Default database name", ui_group="Target"),
                ConfigurationField(name="schema_name", field_type=ConfigurationFieldType.STRING, description="Default schema name", default_value="PUBLIC", ui_group="Target"),
                ConfigurationField(name="role", field_type=ConfigurationFieldType.STRING, description="Snowflake user role", ui_group="Authentication"),
                ConfigurationField(name="username", field_type=ConfigurationFieldType.STRING, description="Snowflake username", is_required=True, ui_group="Authentication"),
                ConfigurationField(name="password_ref", field_type=ConfigurationFieldType.SECRET_REF, description="Reference pointer to Snowflake password secret", ui_group="Authentication"),
                ConfigurationField(name="token_ref", field_type=ConfigurationFieldType.SECRET_REF, description="Reference pointer to OAuth/PAT token secret", condition=ConfigurationCondition.when_field_equals("authenticator", "oauth"), ui_group="Authentication"),
                ConfigurationField(name="authenticator", field_type=ConfigurationFieldType.STRING, description="Authenticator mechanism (e.g. 'snowflake', 'externalbrowser', 'oauth')", default_value="snowflake", ui_group="Authentication"),
            ),
        )

    elif pid == "bigquery":
        return ConfigurationSchema(
            schema_id="bigquery-connection-config",
            schema_version="1.0.0",
            description="Configuration schema for Google Cloud BigQuery provider",
            fields=(
                ConfigurationField(name="project_id", field_type=ConfigurationFieldType.STRING, description="Google Cloud Project ID", is_required=True, ui_group="Target"),
                ConfigurationField(name="dataset", field_type=ConfigurationFieldType.STRING, description="Default BigQuery dataset identifier", ui_group="Target"),
                ConfigurationField(name="service_account_json_ref", field_type=ConfigurationFieldType.SECRET_REF, description="Reference pointer to GCP Service Account JSON key secret (omitted if using ambient ADC)", ui_group="Authentication"),
                ConfigurationField(name="location", field_type=ConfigurationFieldType.STRING, description="Dataset regional/multi-regional location", default_value="US", ui_group="Connection"),
            ),
        )

    elif pid == "redshift":
        return ConfigurationSchema(
            schema_id="redshift-connection-config",
            schema_version="1.0.0",
            description="Configuration schema for Amazon Redshift provider",
            fields=(
                ConfigurationField(name="host", field_type=ConfigurationFieldType.STRING, description="Redshift cluster endpoint hostname", is_required=True, ui_group="Network"),
                ConfigurationField(name="port", field_type=ConfigurationFieldType.INTEGER, description="Redshift port", default_value=5439, constraint=ConfigurationConstraint(min_value=1, max_value=65535), ui_group="Network"),
                ConfigurationField(name="database_name", field_type=ConfigurationFieldType.STRING, description="Target database name", is_required=True, ui_group="Target"),
                ConfigurationField(name="username", field_type=ConfigurationFieldType.STRING, description="Database username", is_required=True, ui_group="Authentication"),
                ConfigurationField(name="password_ref", field_type=ConfigurationFieldType.SECRET_REF, description="Reference pointer to Redshift password secret", is_required=True, ui_group="Authentication"),
                ConfigurationField(name="cluster_identifier", field_type=ConfigurationFieldType.STRING, description="AWS Redshift cluster identifier", ui_group="Target"),
                ConfigurationField(name="region", field_type=ConfigurationFieldType.STRING, description="AWS Region", default_value="us-east-1", ui_group="Network"),
            ),
        )

    elif pid == "databricks":
        return ConfigurationSchema(
            schema_id="databricks-connection-config",
            schema_version="1.0.0",
            description="Configuration schema for Databricks Lakehouse SQL provider",
            fields=(
                ConfigurationField(name="host", field_type=ConfigurationFieldType.STRING, description="Databricks workspace server hostname (e.g. dbc-xxx.cloud.databricks.com)", is_required=True, ui_group="Network"),
                ConfigurationField(name="http_path", field_type=ConfigurationFieldType.STRING, description="HTTP Path to SQL Warehouse or compute endpoint", is_required=True, ui_group="Network"),
                ConfigurationField(name="access_token_ref", field_type=ConfigurationFieldType.SECRET_REF, description="Reference pointer to Databricks Personal Access Token (PAT)", is_required=True, ui_group="Authentication"),
                ConfigurationField(name="catalog", field_type=ConfigurationFieldType.STRING, description="Unity Catalog name", ui_group="Target"),
                ConfigurationField(name="schema_name", field_type=ConfigurationFieldType.STRING, description="Default schema name", default_value="default", ui_group="Target"),
            ),
        )

    elif pid == "mongodb":
        return ConfigurationSchema(
            schema_id="mongodb-connection-config",
            schema_version="1.0.0",
            description="Configuration schema for MongoDB document database provider",
            fields=(
                ConfigurationField(name="host", field_type=ConfigurationFieldType.STRING, description="MongoDB primary hostname", ui_group="Network"),
                ConfigurationField(name="port", field_type=ConfigurationFieldType.INTEGER, description="MongoDB port", default_value=27017, constraint=ConfigurationConstraint(min_value=1, max_value=65535), ui_group="Network"),
                ConfigurationField(name="endpoints", field_type=ConfigurationFieldType.LIST, description="List of replica set node addresses (host:port)", ui_group="Network"),
                ConfigurationField(name="database_name", field_type=ConfigurationFieldType.STRING, description="Default database name", default_value="admin", ui_group="Target"),
                ConfigurationField(name="username", field_type=ConfigurationFieldType.STRING, description="MongoDB username", ui_group="Authentication"),
                ConfigurationField(name="password_ref", field_type=ConfigurationFieldType.SECRET_REF, description="Reference pointer to MongoDB password secret", ui_group="Authentication"),
                ConfigurationField(name="auth_source", field_type=ConfigurationFieldType.STRING, description="Authentication database", default_value="admin", ui_group="Authentication"),
                ConfigurationField(name="replica_set", field_type=ConfigurationFieldType.STRING, description="Replica set name", ui_group="Connection"),
            ),
        )

    elif pid in ("cassandra", "scylladb"):
        return ConfigurationSchema(
            schema_id=f"{pid}-connection-config",
            schema_version="1.0.0",
            description=f"Configuration schema for {pid.title()} distributed ring database provider",
            fields=(
                ConfigurationField(name="host", field_type=ConfigurationFieldType.STRING, description="Initial contact point hostname", ui_group="Network"),
                ConfigurationField(name="port", field_type=ConfigurationFieldType.INTEGER, description="CQL native transport port", default_value=9042, constraint=ConfigurationConstraint(min_value=1, max_value=65535), ui_group="Network"),
                ConfigurationField(name="endpoints", field_type=ConfigurationFieldType.LIST, description="List of cluster contact points", ui_group="Network"),
                ConfigurationField(name="database_name", field_type=ConfigurationFieldType.STRING, description="Default keyspace name", ui_group="Target"),
                ConfigurationField(name="username", field_type=ConfigurationFieldType.STRING, description="CQL username", ui_group="Authentication"),
                ConfigurationField(name="password_ref", field_type=ConfigurationFieldType.SECRET_REF, description="Reference pointer to CQL password secret", ui_group="Authentication"),
                ConfigurationField(name="protocol_version", field_type=ConfigurationFieldType.INTEGER, description="CQL binary protocol version", default_value=4, ui_group="Connection"),
            ),
        )

    elif pid == "neo4j":
        return ConfigurationSchema(
            schema_id="neo4j-connection-config",
            schema_version="1.0.0",
            description="Configuration schema for Neo4j graph database provider",
            fields=(
                ConfigurationField(name="host", field_type=ConfigurationFieldType.STRING, description="Neo4j server hostname", is_required=True, ui_group="Network"),
                ConfigurationField(name="port", field_type=ConfigurationFieldType.INTEGER, description="Bolt protocol port", default_value=7687, constraint=ConfigurationConstraint(min_value=1, max_value=65535), ui_group="Network"),
                ConfigurationField(name="database_name", field_type=ConfigurationFieldType.STRING, description="Target graph database name", default_value="neo4j", ui_group="Target"),
                ConfigurationField(name="username", field_type=ConfigurationFieldType.STRING, description="Neo4j username", is_required=True, ui_group="Authentication"),
                ConfigurationField(name="password_ref", field_type=ConfigurationFieldType.SECRET_REF, description="Reference pointer to Neo4j password secret", is_required=True, ui_group="Authentication"),
            ),
        )

    elif pid in ("redis", "keydb"):
        return ConfigurationSchema(
            schema_id=f"{pid}-connection-config",
            schema_version="1.0.0",
            description=f"Configuration schema for {pid.upper()} in-memory key-value provider",
            fields=(
                ConfigurationField(name="host", field_type=ConfigurationFieldType.STRING, description=f"{pid.upper()} server hostname", is_required=True, ui_group="Network"),
                ConfigurationField(name="port", field_type=ConfigurationFieldType.INTEGER, description=f"{pid.upper()} server port", default_value=6379, constraint=ConfigurationConstraint(min_value=1, max_value=65535), ui_group="Network"),
                ConfigurationField(name="database_name", field_type=ConfigurationFieldType.STRING, description="Redis database index", default_value="0", ui_group="Target"),
                ConfigurationField(name="username", field_type=ConfigurationFieldType.STRING, description="ACL username (optional)", ui_group="Authentication"),
                ConfigurationField(name="password_ref", field_type=ConfigurationFieldType.SECRET_REF, description="Reference pointer to Redis AUTH secret", ui_group="Authentication"),
            ),
        )

    elif pid in ("elasticsearch", "opensearch"):
        return ConfigurationSchema(
            schema_id=f"{pid}-connection-config",
            schema_version="1.0.0",
            description=f"Configuration schema for {pid.title()} search cluster provider supporting multi-node hosts and API keys",
            fields=(
                ConfigurationField(name="host", field_type=ConfigurationFieldType.STRING, description=f"{pid.title()} cluster primary host", ui_group="Network"),
                ConfigurationField(name="port", field_type=ConfigurationFieldType.INTEGER, description=f"{pid.title()} HTTP REST port", default_value=9200, constraint=ConfigurationConstraint(min_value=1, max_value=65535), ui_group="Network"),
                ConfigurationField(name="endpoints", field_type=ConfigurationFieldType.LIST, description="List of cluster node URLs or host:port pairs", ui_group="Network"),
                ConfigurationField(name="username", field_type=ConfigurationFieldType.STRING, description="Basic auth username", ui_group="Authentication"),
                ConfigurationField(name="password_ref", field_type=ConfigurationFieldType.SECRET_REF, description="Reference pointer to basic auth password secret", ui_group="Authentication"),
                ConfigurationField(name="api_key_ref", field_type=ConfigurationFieldType.SECRET_REF, description="Reference pointer to API Key secret", ui_group="Authentication"),
            ),
        )

    elif pid == "kafka":
        return ConfigurationSchema(
            schema_id="kafka-connection-config",
            schema_version="1.0.0",
            description="Configuration schema for Apache Kafka cluster provider supporting multi-brokers, SASL (PLAIN, SCRAM), and TLS",
            fields=(
                ConfigurationField(name="host", field_type=ConfigurationFieldType.STRING, description="Primary bootstrap broker hostname", ui_group="Network"),
                ConfigurationField(name="port", field_type=ConfigurationFieldType.INTEGER, description="Bootstrap broker port", default_value=9092, constraint=ConfigurationConstraint(min_value=1, max_value=65535), ui_group="Network"),
                ConfigurationField(name="endpoints", field_type=ConfigurationFieldType.LIST, description="List of Kafka bootstrap servers (host:port)", ui_group="Network"),
                ConfigurationField(name="security_protocol", field_type=ConfigurationFieldType.STRING, description="Kafka security protocol", default_value="PLAINTEXT", constraint=ConfigurationConstraint(allowed_values=("PLAINTEXT", "SSL", "SASL_PLAINTEXT", "SASL_SSL")), ui_group="Security"),
                ConfigurationField(name="sasl_mechanism", field_type=ConfigurationFieldType.STRING, description="SASL authentication mechanism", default_value="PLAIN", constraint=ConfigurationConstraint(allowed_values=("PLAIN", "SCRAM-SHA-256", "SCRAM-SHA-512")), ui_group="Authentication"),
                ConfigurationField(name="username", field_type=ConfigurationFieldType.STRING, description="SASL username / API key", ui_group="Authentication"),
                ConfigurationField(name="password_ref", field_type=ConfigurationFieldType.SECRET_REF, description="Reference pointer to SASL password / API secret", ui_group="Authentication"),
                ConfigurationField(name="client_id", field_type=ConfigurationFieldType.STRING, description="Kafka client identifier", default_value="akaal-engine-connection", ui_group="Connection"),
                ConfigurationField(name="group_id", field_type=ConfigurationFieldType.STRING, description="Default Kafka consumer group identifier", ui_group="Connection"),
            ),
        )

    elif pid == "kinesis":
        return ConfigurationSchema(
            schema_id="kinesis-connection-config",
            schema_version="1.0.0",
            description="Configuration schema for AWS Kinesis streaming provider supporting explicit/STS temporary credentials and custom endpoints",
            fields=(
                ConfigurationField(name="region", field_type=ConfigurationFieldType.STRING, description="AWS Region", default_value="us-east-1", ui_group="Network"),
                ConfigurationField(name="endpoint_url", field_type=ConfigurationFieldType.STRING, description="Custom endpoint URL for VPC endpoints or LocalStack", ui_group="Network"),
                ConfigurationField(name="access_key_id_ref", field_type=ConfigurationFieldType.SECRET_REF, description="Reference pointer to AWS Access Key ID secret (omitted if using ambient IAM)", ui_group="Authentication"),
                ConfigurationField(name="secret_access_key_ref", field_type=ConfigurationFieldType.SECRET_REF, description="Reference pointer to AWS Secret Access Key secret", ui_group="Authentication"),
                ConfigurationField(name="session_token_ref", field_type=ConfigurationFieldType.SECRET_REF, description="Reference pointer to AWS STS Temporary Session Token secret", ui_group="Authentication"),
                ConfigurationField(name="stream_name", field_type=ConfigurationFieldType.STRING, description="Target Kinesis stream name", ui_group="Target"),
            ),
        )

    elif pid == "eventhubs":
        return ConfigurationSchema(
            schema_id="eventhubs-connection-config",
            schema_version="1.0.0",
            description="Configuration schema for Azure Event Hubs streaming provider",
            fields=(
                ConfigurationField(name="namespace", field_type=ConfigurationFieldType.STRING, description="Azure Event Hubs namespace", is_required=True, ui_group="Network"),
                ConfigurationField(name="eventhub_name", field_type=ConfigurationFieldType.STRING, description="Event Hub instance name", ui_group="Target"),
                ConfigurationField(name="connection_string_ref", field_type=ConfigurationFieldType.SECRET_REF, description="Reference pointer to Event Hubs connection string secret", is_required=True, ui_group="Authentication"),
            ),
        )

    elif pid == "pubsub":
        return ConfigurationSchema(
            schema_id="pubsub-connection-config",
            schema_version="1.0.0",
            description="Configuration schema for Google Cloud Pub/Sub messaging provider supporting explicit service accounts and ADC",
            fields=(
                ConfigurationField(name="project_id", field_type=ConfigurationFieldType.STRING, description="Google Cloud Project ID", is_required=True, ui_group="Target"),
                ConfigurationField(name="topic_id", field_type=ConfigurationFieldType.STRING, description="Target Pub/Sub topic identifier", ui_group="Target"),
                ConfigurationField(name="subscription_id", field_type=ConfigurationFieldType.STRING, description="Source Pub/Sub subscription identifier", ui_group="Target"),
                ConfigurationField(name="service_account_json_ref", field_type=ConfigurationFieldType.SECRET_REF, description="Reference pointer to GCP Service Account JSON key secret (omitted if using ambient ADC)", ui_group="Authentication"),
            ),
        )

    elif pid == "s3":
        return ConfigurationSchema(
            schema_id="s3-connection-config",
            schema_version="1.0.0",
            description="Configuration schema for AWS S3 Object Storage provider supporting explicit, STS temporary session tokens, and custom endpoints",
            fields=(
                ConfigurationField(name="region", field_type=ConfigurationFieldType.STRING, description="AWS Region", default_value="us-east-1", ui_group="Network"),
                ConfigurationField(name="endpoint_url", field_type=ConfigurationFieldType.STRING, description="Custom S3 endpoint URL (for MinIO, Ceph, LocalStack, or VPC endpoints)", ui_group="Network"),
                ConfigurationField(name="bucket_name", field_type=ConfigurationFieldType.STRING, description="Target S3 bucket name", ui_group="Target"),
                ConfigurationField(name="access_key_id_ref", field_type=ConfigurationFieldType.SECRET_REF, description="Reference pointer to AWS Access Key ID secret (omitted if using ambient IAM)", ui_group="Authentication"),
                ConfigurationField(name="secret_access_key_ref", field_type=ConfigurationFieldType.SECRET_REF, description="Reference pointer to AWS Secret Access Key secret", ui_group="Authentication"),
                ConfigurationField(name="session_token_ref", field_type=ConfigurationFieldType.SECRET_REF, description="Reference pointer to AWS STS Temporary Session Token secret", ui_group="Authentication"),
            ),
        )

    elif pid == "gcs":
        return ConfigurationSchema(
            schema_id="gcs-connection-config",
            schema_version="1.0.0",
            description="Configuration schema for Google Cloud Storage (GCS) provider supporting explicit service accounts and ADC",
            fields=(
                ConfigurationField(name="project_id", field_type=ConfigurationFieldType.STRING, description="Google Cloud Project ID", ui_group="Target"),
                ConfigurationField(name="bucket_name", field_type=ConfigurationFieldType.STRING, description="Target GCS bucket name", ui_group="Target"),
                ConfigurationField(name="service_account_json_ref", field_type=ConfigurationFieldType.SECRET_REF, description="Reference pointer to GCP Service Account JSON key secret (omitted if using ambient ADC)", ui_group="Authentication"),
            ),
        )

    elif pid == "azure_blob":
        return ConfigurationSchema(
            schema_id="azure-blob-connection-config",
            schema_version="1.0.0",
            description="Configuration schema for Azure Blob Storage provider supporting Connection String, Account Key, SAS, and Managed Identity",
            fields=(
                ConfigurationField(name="account_name", field_type=ConfigurationFieldType.STRING, description="Azure Storage account name", ui_group="Target"),
                ConfigurationField(name="container_name", field_type=ConfigurationFieldType.STRING, description="Azure Blob container name", ui_group="Target"),
                ConfigurationField(name="connection_string_ref", field_type=ConfigurationFieldType.SECRET_REF, description="Reference pointer to Azure Storage connection string secret", ui_group="Authentication"),
                ConfigurationField(name="account_key_ref", field_type=ConfigurationFieldType.SECRET_REF, description="Reference pointer to Azure Storage account key secret", ui_group="Authentication"),
                ConfigurationField(name="sas_token_ref", field_type=ConfigurationFieldType.SECRET_REF, description="Reference pointer to Azure SAS token secret", ui_group="Authentication"),
                ConfigurationField(name="endpoint_url", field_type=ConfigurationFieldType.STRING, description="Custom Blob Service endpoint URL (for Azurite or Private Endpoints)", ui_group="Network"),
            ),
        )

    elif pid == "minio":
        return ConfigurationSchema(
            schema_id="minio-connection-config",
            schema_version="1.0.0",
            description="Configuration schema for MinIO Object Storage provider",
            fields=(
                ConfigurationField(name="host", field_type=ConfigurationFieldType.STRING, description="MinIO server hostname or IP", default_value="localhost", is_required=True, ui_group="Network"),
                ConfigurationField(name="port", field_type=ConfigurationFieldType.INTEGER, description="MinIO S3 API port", default_value=9000, constraint=ConfigurationConstraint(min_value=1, max_value=65535), ui_group="Network"),
                ConfigurationField(name="bucket_name", field_type=ConfigurationFieldType.STRING, description="Target bucket name", ui_group="Target"),
                ConfigurationField(name="access_key_id_ref", field_type=ConfigurationFieldType.SECRET_REF, description="Reference pointer to MinIO access key secret", is_required=True, ui_group="Authentication"),
                ConfigurationField(name="secret_access_key_ref", field_type=ConfigurationFieldType.SECRET_REF, description="Reference pointer to MinIO secret key secret", is_required=True, ui_group="Authentication"),
            ),
        )

    elif pid == "hdfs":
        return ConfigurationSchema(
            schema_id="hdfs-connection-config",
            schema_version="1.0.0",
            description="Configuration schema for Hadoop Distributed File System (HDFS) provider",
            fields=(
                ConfigurationField(name="host", field_type=ConfigurationFieldType.STRING, description="Hadoop NameNode hostname or IP address", is_required=True, ui_group="Network"),
                ConfigurationField(name="port", field_type=ConfigurationFieldType.INTEGER, description="NameNode HTTP (WebHDFS: 9870) or RPC (8020) port", default_value=9870, constraint=ConfigurationConstraint(min_value=1, max_value=65535), ui_group="Network"),
                ConfigurationField(name="user", field_type=ConfigurationFieldType.STRING, description="HDFS username", default_value="hdfs", ui_group="Authentication"),
                ConfigurationField(name="root_path", field_type=ConfigurationFieldType.STRING, description="HDFS root directory path", default_value="/", ui_group="Target"),
                ConfigurationField(name="use_webhdfs", field_type=ConfigurationFieldType.BOOLEAN, description="Use WebHDFS REST API rather than native RPC", default_value=True, ui_group="Connection"),
            ),
        )

    return None
