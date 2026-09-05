"""
akaalEngine.discovery.models.cdc
================================
CDC prerequisites, log mining readiness, and starting commit coordinates fact models.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping, Optional, Sequence, Tuple


class CDCMechanism(str, Enum):
    """Underlying physical CDC extraction mechanism."""
    ORACLE_LOGMINER = "ORACLE_LOGMINER"
    POSTGRES_LOGICAL_DECODING = "POSTGRES_LOGICAL_DECODING"
    MYSQL_BINLOG = "MYSQL_BINLOG"
    MSSQL_CDC = "MSSQL_CDC"
    MSSQL_CHANGE_TRACKING = "MSSQL_CHANGE_TRACKING"
    MONGO_CHANGE_STREAMS = "MONGO_CHANGE_STREAMS"
    SCYLLA_CDC = "SCYLLA_CDC"
    CASSANDRA_CDC = "CASSANDRA_CDC"
    KAFKA_STREAMING = "KAFKA_STREAMING"
    KINESIS_DATA_STREAMS = "KINESIS_DATA_STREAMS"
    GCP_PUBSUB = "GCP_PUBSUB"
    AZURE_EVENT_HUBS = "AZURE_EVENT_HUBS"
    SNOWFLAKE_STREAMS = "SNOWFLAKE_STREAMS"
    BIGQUERY_CDC = "BIGQUERY_CDC"
    DELTA_CHANGE_DATA_FEED = "DELTA_CHANGE_DATA_FEED"
    REDIS_STREAMS_CDC = "REDIS_STREAMS_CDC"
    ELASTICSEARCH_CHANGES = "ELASTICSEARCH_CHANGES"
    OPENSEARCH_CHANGES = "OPENSEARCH_CHANGES"
    NEO4J_CDC = "NEO4J_CDC"
    COCKROACHDB_CHANGEFEED = "COCKROACHDB_CHANGEFEED"
    RABBITMQ_STREAMS = "RABBITMQ_STREAMS"
    PULSAR_STREAMING = "PULSAR_STREAMING"
    DYNAMODB_STREAMS = "DYNAMODB_STREAMS"
    COUCHBASE_DCP = "COUCHBASE_DCP"
    TIDB_CDC = "TIDB_CDC"
    POLLING_WATERMARK = "POLLING_WATERMARK"
    PROVIDER_NA = "PROVIDER_NA"
    UNSUPPORTED = "UNSUPPORTED"


@dataclass(frozen=True)
class StartingCommitPosition:
    """Discovered starting log mining or replication coordinates."""
    lsn: Optional[str] = None
    scn: Optional[int] = None
    binlog_file: Optional[str] = None
    binlog_position: Optional[int] = None
    gtid_set: Optional[str] = None
    timestamp_iso: Optional[str] = None
    stream_offsets: Mapping[str, int] = field(default_factory=lambda: MappingProxyType({}))

    def __post_init__(self) -> None:
        if not isinstance(self.stream_offsets, MappingProxyType):
            object.__setattr__(self, "stream_offsets", MappingProxyType(dict(self.stream_offsets)))

    def to_dict(self) -> dict[str, Any]:
        return {
            "lsn": self.lsn,
            "scn": self.scn,
            "binlog_file": self.binlog_file,
            "binlog_position": self.binlog_position,
            "gtid_set": self.gtid_set,
            "timestamp_iso": self.timestamp_iso,
            "stream_offsets": dict(self.stream_offsets),
        }


@dataclass(frozen=True)
class CDCPrerequisiteSnapshot:
    """Discovered CDC operational prerequisites and cutover coordinates."""
    is_cdc_ready: bool = False
    mechanism: CDCMechanism = CDCMechanism.UNSUPPORTED
    starting_position: Optional[StartingCommitPosition] = None
    # Oracle facts
    is_archivelog_enabled: Optional[bool] = None
    is_supplemental_logging_enabled: Optional[bool] = None
    # Postgres facts
    is_wal_level_logical: Optional[bool] = None
    max_replication_slots: Optional[int] = None
    available_replication_slots: Optional[int] = None
    # MySQL / MariaDB facts
    is_binlog_enabled: Optional[bool] = None
    is_binlog_format_row: Optional[bool] = None
    is_gtid_enabled: Optional[bool] = None
    # MSSQL facts
    is_cdc_enabled_on_database: Optional[bool] = None
    is_change_tracking_enabled_on_database: Optional[bool] = None
    # Mongo facts
    is_replica_set: Optional[bool] = None
    oplog_size_mb: Optional[int] = None
    # Blocker reasons if not ready
    blocker_reasons: Tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not isinstance(self.blocker_reasons, tuple):
            object.__setattr__(self, "blocker_reasons", tuple(self.blocker_reasons))

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_cdc_ready": self.is_cdc_ready,
            "mechanism": self.mechanism.value,
            "starting_position": self.starting_position.to_dict() if self.starting_position else None,
            "is_archivelog_enabled": self.is_archivelog_enabled,
            "is_supplemental_logging_enabled": self.is_supplemental_logging_enabled,
            "is_wal_level_logical": self.is_wal_level_logical,
            "max_replication_slots": self.max_replication_slots,
            "available_replication_slots": self.available_replication_slots,
            "is_binlog_enabled": self.is_binlog_enabled,
            "is_binlog_format_row": self.is_binlog_format_row,
            "is_gtid_enabled": self.is_gtid_enabled,
            "is_cdc_enabled_on_database": self.is_cdc_enabled_on_database,
            "is_change_tracking_enabled_on_database": self.is_change_tracking_enabled_on_database,
            "is_replica_set": self.is_replica_set,
            "oplog_size_mb": self.oplog_size_mb,
            "blocker_reasons": list(self.blocker_reasons),
        }
