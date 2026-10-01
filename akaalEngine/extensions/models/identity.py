"""
akaalEngine.extensions.models.identity
======================================
Immutable, normalized identity types for extensions, providers, strategies, authorities, and registry generations.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional


_VALID_IDENTIFIER_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_\-\.]{0,127}$")


_CANONICAL_PROVIDERS = {
    'azure_blob', 'bigquery', 'cassandra', 'clickhouse', 'cockroachdb', 'cosmosdb',
    'couchbase', 'databricks', 'dynamodb', 'elasticsearch', 'eventhubs', 'gcs',
    'hdfs', 'ibm_db2', 'influxdb', 'informix', 'kafka', 'keydb', 'kinesis',
    'mariadb', 'minio', 'mongodb', 'mssql', 'mysql', 'neo4j', 'oci_object_storage',
    'opensearch', 'oracle', 'postgresql', 'pubsub', 'pulsar', 'rabbitmq', 'redis',
    'redshift', 's3', 'salesforce', 'sap_application', 'sap_ase', 'sap_hana',
    'scylladb', 'servicenow', 'singlestore', 'snowflake', 'spanner', 'sqlite',
    'teradata', 'tidb', 'vertica', 'yugabytedb'
}

_PROVIDER_ALIASES = {
    'oracle database': 'oracle',
    'oracle 19c': 'oracle',
    'oracle 21c': 'oracle',
    'oracle 19c enterprise rac': 'oracle',
    'oracle enterprise': 'oracle',
    'postgresql database': 'postgresql',
    'postgres': 'postgresql',
    'aws aurora postgresql': 'postgresql',
    'aws aurora postgresql cluster': 'postgresql',
    'aurora postgresql': 'postgresql',
    'aurora_postgresql': 'postgresql',
    'mysql database': 'mysql',
    'dev mysql local replica': 'mysql',
    'aws aurora mysql': 'mysql',
    'aurora mysql': 'mysql',
    'aurora_mysql': 'mysql',
    'sql server': 'mssql',
    'microsoft sql server': 'mssql',
    'sqlserver': 'mssql',
    'azure sql': 'mssql',
    'apache kafka': 'kafka',
    'google bigquery': 'bigquery',
    'amazon dynamodb': 'dynamodb',
    'apache cassandra': 'cassandra',
    'ibm db2': 'ibm_db2',
    'db2': 'ibm_db2',
    'sap hana': 'sap_hana',
    'sap ase': 'sap_ase',
    'sap application': 'sap_application',
    'amazon redshift': 'redshift',
    'google cloud storage': 'gcs',
    'amazon s3': 's3',
    'azure blob storage': 'azure_blob',
    'amazon kinesis': 'kinesis',
    'google pubsub': 'pubsub',
    'apache pulsar': 'pulsar',
    'azure eventhubs': 'eventhubs',
    'azure cosmosdb': 'cosmosdb',
    'google spanner': 'spanner',
    'oracle cloud storage': 'oci_object_storage',
    'sqlite3': 'sqlite',
    'elastic': 'elasticsearch',
    'couchbase server': 'couchbase',
    'scylla': 'scylladb',
    'yugabyte': 'yugabytedb',
}


def normalize_provider_slug(val: str) -> str:
    """Universally maps provider names/aliases across all engines to canonical provider IDs."""
    if not val or not isinstance(val, str):
        return val
    cleaned = val.strip().lower()
    if cleaned in _CANONICAL_PROVIDERS:
        return cleaned
    if cleaned in _PROVIDER_ALIASES:
        return _PROVIDER_ALIASES[cleaned]
    slug = cleaned.replace(' ', '_').replace('-', '_')
    if slug in _CANONICAL_PROVIDERS:
        return slug
    if slug in _PROVIDER_ALIASES:
        return _PROVIDER_ALIASES[slug]
    for suffix in ('_database', '_db', '_cluster', '_enterprise', '_rac', '_local_replica'):
        if slug.endswith(suffix):
            cand = slug[:-len(suffix)].rstrip('_')
            if cand in _CANONICAL_PROVIDERS:
                return cand
            if cand in _PROVIDER_ALIASES:
                return _PROVIDER_ALIASES[cand]
    for key, tgt in _PROVIDER_ALIASES.items():
        if key in cleaned:
            return tgt
    for canon in _CANONICAL_PROVIDERS:
        if canon in slug:
            return canon
    sanitized = re.sub(r'[^a-z0-9_\-\.]', '_', slug).strip('_')
    return sanitized or cleaned


def normalize_identifier(val: str, field_name: str = "identifier") -> str:
    """Normalizes an identifier to lowercase stripped string and validates format."""
    if not val or not isinstance(val, str):
        raise ValueError(f"{field_name} must be a non-empty string.")
    normalized = val.strip().lower()
    if not normalized:
        raise ValueError(f"{field_name} cannot be empty or whitespace.")
    if not _VALID_IDENTIFIER_PATTERN.match(normalized):
        raise ValueError(
            f"Invalid {field_name} '{normalized}'. Must match ^[a-z0-9][a-z0-9_\\-\\.]{{0,127}}$"
        )
    return normalized


@dataclass(frozen=True, order=True)
class ExtensionId:
    """Canonical identifier for an extension package or bundle."""
    value: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", normalize_identifier(self.value, "ExtensionId"))

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, order=True)
class ProviderId:
    """Canonical identifier for a data provider (e.g. 'postgresql', 'snowflake', 's3')."""
    value: str

    def __post_init__(self) -> None:
        norm_val = normalize_provider_slug(self.value)
        object.__setattr__(self, "value", normalize_identifier(norm_val, "ProviderId"))

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, order=True)
class AuthorityId:
    """Canonical identifier for an Engine authority (e.g. 'connection', 'discovery', 'schema', 'transport', 'change_capture')."""
    value: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", normalize_identifier(self.value, "AuthorityId"))

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, order=True)
class StrategyId:
    """Canonical identifier for an authority-specific strategy implementation (e.g. 'postgres-pgcopy', 'oracle-logminer')."""
    value: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", normalize_identifier(self.value, "StrategyId"))

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, order=True)
class RegistryGeneration:
    """Monotonically increasing sequence tracking published immutable registry states."""
    value: int

    def __post_init__(self) -> None:
        if not isinstance(self.value, int) or self.value < 1:
            raise ValueError(f"RegistryGeneration must be a positive integer >= 1, got {self.value}.")

    def next(self) -> RegistryGeneration:
        return RegistryGeneration(self.value + 1)

    def __str__(self) -> str:
        return str(self.value)
