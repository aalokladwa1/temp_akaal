"""
akaalEngine.transport.drivers.registry
=========================================
Dynamic provider -> (SourceReader, TargetWriter) driver registry for Authority #9 Transport.

Prior to this module, `TransportAuthority` only knew about SourceReader/TargetWriter
implementations wired in as fixed imports at the top of `transport/api.py` (files,
generic_sql, oracle, postgres) -- any other provider had NO canonical physical data-plane
path at all, regardless of what its Connection/Discovery/Extensions capability truth
declared. This registry is the smallest correct extension point: a plain dynamic mapping
(not a hardcoded if/elif switch) that lets each provider-native transport driver module
register itself at import time, so providers 39-48 can be added later purely by adding a
new driver module and calling `register_transport_driver(...)` -- no change to
`TransportAuthority` or this registry itself required.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Optional, Type

from akaalEngine.transport.drivers.base import SourceReader, TargetWriter


@dataclass(frozen=True)
class TransportDriverRegistration:
    """A provider's registered physical transport driver classes."""
    provider_id: str
    reader_cls: Optional[Type[SourceReader]]
    writer_cls: Optional[Type[TargetWriter]]


def normalize_provider_id(provider_id: str) -> str:
    """Canonical Provider Identity Authority.
    Normalizes product-facing display names, aliases, and vendor titles to physical driver keys.
    """
    if not provider_id or not isinstance(provider_id, str):
        return ""
    clean = provider_id.strip().lower()
    clean = clean.replace(" database", "").replace(" db", "")
    alias_map = {
        "microsoft sql server": "mssql",
        "microsoft_sql_server": "mssql",
        "sql server": "mssql",
        "sqlserver": "mssql",
        "sql_server": "mssql",
        "postgresql": "postgres",
        "postgre sql": "postgres",
        "oracle database": "oracle",
        "oracle_database": "oracle",
        "mysql database": "mysql",
        "mysql_database": "mysql",
        "sqlite3": "sqlite",
        "amazon redshift": "redshift",
        "google bigquery": "bigquery",
    }
    return alias_map.get(clean, clean)


class TransportDriverRegistry:
    """Thread-naive (import-time-populated, read-mostly) provider -> driver registry."""

    def __init__(self) -> None:
        self._drivers: Dict[str, TransportDriverRegistration] = {}

    def register(
        self,
        provider_id: str,
        reader_cls: Optional[Type[SourceReader]] = None,
        writer_cls: Optional[Type[TargetWriter]] = None,
    ) -> None:
        pid = normalize_provider_id(provider_id)
        existing = self._drivers.get(pid)
        merged_reader = reader_cls or (existing.reader_cls if existing else None)
        merged_writer = writer_cls or (existing.writer_cls if existing else None)
        reg = TransportDriverRegistration(
            provider_id=pid,
            reader_cls=merged_reader,
            writer_cls=merged_writer,
        )
        self._drivers[pid] = reg
        raw_clean = provider_id.strip().lower()
        if raw_clean != pid:
            self._drivers[raw_clean] = reg

    def get(self, provider_id: str) -> Optional[TransportDriverRegistration]:
        pid = normalize_provider_id(provider_id)
        return self._drivers.get(pid) or self._drivers.get(provider_id.strip().lower())

    def is_registered(self, provider_id: str) -> bool:
        pid = normalize_provider_id(provider_id)
        return pid in self._drivers or provider_id.strip().lower() in self._drivers

    def list_providers(self) -> list[str]:
        return sorted(self._drivers.keys())


default_transport_driver_registry = TransportDriverRegistry()


def register_transport_driver(
    provider_id: str,
    reader_cls: Optional[Type[SourceReader]] = None,
    writer_cls: Optional[Type[TargetWriter]] = None,
) -> None:
    """Module-level convenience for a provider-native driver module to self-register on import."""
    default_transport_driver_registry.register(provider_id, reader_cls=reader_cls, writer_cls=writer_cls)


def _bootstrap_default_drivers() -> None:
    # 1. MySQL / MariaDB
    try:
        from akaalEngine.transport.drivers.mysql import MySQLSourceReader, MySQLTargetWriter
        register_transport_driver("mysql", MySQLSourceReader, MySQLTargetWriter)
        register_transport_driver("mariadb", MySQLSourceReader, MySQLTargetWriter)
    except Exception:
        pass

    # 2. Oracle
    try:
        from akaalEngine.transport.drivers.oracle import OracleSourceReader, OracleTargetWriter
        register_transport_driver("oracle", OracleSourceReader, OracleTargetWriter)
    except Exception:
        pass

    # 3. PostgreSQL
    try:
        from akaalEngine.transport.drivers.postgres import PostgreSQLTargetWriter
        from akaalEngine.transport.drivers.generic_sql import GenericSQLSourceReader
        register_transport_driver("postgres", GenericSQLSourceReader, PostgreSQLTargetWriter)
        register_transport_driver("postgresql", GenericSQLSourceReader, PostgreSQLTargetWriter)
    except Exception:
        pass

    # 4. Generic SQL & Relational DBs / Data Warehouses
    try:
        from akaalEngine.transport.drivers.generic_sql import GenericSQLSourceReader, GenericSQLTargetWriter
        register_transport_driver("generic_sql", GenericSQLSourceReader, GenericSQLTargetWriter)
        register_transport_driver("mssql", GenericSQLSourceReader, GenericSQLTargetWriter)
        register_transport_driver("sqlite", GenericSQLSourceReader, GenericSQLTargetWriter)
        register_transport_driver("ibm_db2", GenericSQLSourceReader, GenericSQLTargetWriter)
        register_transport_driver("singlestore", GenericSQLSourceReader, GenericSQLTargetWriter)
        register_transport_driver("tidb", GenericSQLSourceReader, GenericSQLTargetWriter)
        register_transport_driver("snowflake", GenericSQLSourceReader, GenericSQLTargetWriter)
        register_transport_driver("redshift", GenericSQLSourceReader, GenericSQLTargetWriter)
        register_transport_driver("bigquery", GenericSQLSourceReader, GenericSQLTargetWriter)
        register_transport_driver("databricks", GenericSQLSourceReader, GenericSQLTargetWriter)
    except Exception:
        pass

    # 5. File & Object Storage
    try:
        from akaalEngine.transport.drivers.files import FileSourceReader, FileTargetWriter
        register_transport_driver("file", FileSourceReader, FileTargetWriter)
        register_transport_driver("s3", FileSourceReader, FileTargetWriter)
        register_transport_driver("gcs", FileSourceReader, FileTargetWriter)
        register_transport_driver("azure_blob", FileSourceReader, FileTargetWriter)
        register_transport_driver("hdfs", FileSourceReader, FileTargetWriter)
        register_transport_driver("minio", FileSourceReader, FileTargetWriter)
        register_transport_driver("oci_object_storage", FileSourceReader, FileTargetWriter)
    except Exception:
        pass

    # 6. Provider-Specific Native Drivers
    driver_specs = [
        ("clickhouse", "akaalEngine.transport.drivers.clickhouse", "ClickHouseSourceReader", "ClickHouseTargetWriter"),
        ("cockroachdb", "akaalEngine.transport.drivers.cockroachdb", "GenericSQLSourceReader", "CockroachDBTargetWriter"),
        ("cosmosdb", "akaalEngine.transport.drivers.cosmosdb", "CosmosDBSourceReader", "CosmosDBTargetWriter"),
        ("couchbase", "akaalEngine.transport.drivers.couchbase", "CouchbaseSourceReader", "CouchbaseTargetWriter"),
        ("dynamodb", "akaalEngine.transport.drivers.dynamodb", "DynamoDBSourceReader", "DynamoDBTargetWriter"),
        ("influxdb", "akaalEngine.transport.drivers.influxdb", "InfluxDBSourceReader", "InfluxDBTargetWriter"),
        ("informix", "akaalEngine.transport.drivers.informix", "InformixSourceReader", "InformixTargetWriter"),
        ("pulsar", "akaalEngine.transport.drivers.pulsar", "PulsarSourceReader", "PulsarTargetWriter"),
        ("rabbitmq", "akaalEngine.transport.drivers.rabbitmq", "RabbitMQSourceReader", "RabbitMQTargetWriter"),
        ("salesforce", "akaalEngine.transport.drivers.salesforce", "SalesforceSourceReader", "SalesforceTargetWriter"),
        ("sap_application", "akaalEngine.transport.drivers.sap_application", "SAPApplicationSourceReader", "SAPApplicationTargetWriter"),
        ("sap_ase", "akaalEngine.transport.drivers.sap_ase", "SAPASESourceReader", "SAPASETargetWriter"),
        ("sap_hana", "akaalEngine.transport.drivers.sap_hana", "GenericSQLSourceReader", "SAPHANATargetWriter"),
        ("servicenow", "akaalEngine.transport.drivers.servicenow", "ServiceNowSourceReader", "ServiceNowTargetWriter"),
        ("spanner", "akaalEngine.transport.drivers.spanner", "SpannerSourceReader", "SpannerTargetWriter"),
        ("teradata", "akaalEngine.transport.drivers.teradata", "GenericSQLSourceReader", "TeradataTargetWriter"),
        ("vertica", "akaalEngine.transport.drivers.vertica", "GenericSQLSourceReader", "VerticaTargetWriter"),
        ("yugabytedb", "akaalEngine.transport.drivers.yugabytedb", "GenericSQLSourceReader", "YugabyteDBTargetWriter"),
    ]
    import importlib
    for pid, mod_path, r_name, w_name in driver_specs:
        try:
            mod = importlib.import_module(mod_path)
            r_cls = getattr(mod, r_name, None)
            if r_cls is None and r_name == "GenericSQLSourceReader":
                from akaalEngine.transport.drivers.generic_sql import GenericSQLSourceReader
                r_cls = GenericSQLSourceReader
            w_cls = getattr(mod, w_name, None)
            register_transport_driver(pid, r_cls, w_cls)
        except Exception:
            pass

    # 7. NoSQL / Search / Graph / Streaming Fallbacks for all remaining providers
    remaining_nosql = [
        "cassandra", "scylladb", "mongodb", "redis", "keydb",
        "elasticsearch", "opensearch", "neo4j",
        "kafka", "eventhubs", "kinesis", "pubsub"
    ]
    try:
        from akaalEngine.transport.drivers.base import GenericNoSQLSourceReader, GenericNoSQLTargetWriter
        for pid in remaining_nosql:
            if not default_transport_driver_registry.is_registered(pid):
                register_transport_driver(pid, GenericNoSQLSourceReader, GenericNoSQLTargetWriter)
    except Exception:
        pass

_bootstrap_default_drivers()


