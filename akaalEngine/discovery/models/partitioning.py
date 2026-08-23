"""
akaalEngine.discovery.models.partitioning
========================================
Physical table partitioning, sharding, and distribution fact models.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping, Optional, Sequence, Tuple


class PartitionStrategy(str, Enum):
    """Partitioning and physical distribution strategies."""
    NONE = "NONE"
    RANGE = "RANGE"
    LIST = "LIST"
    HASH = "HASH"
    COMPOSITE = "COMPOSITE"
    INTERVAL = "INTERVAL"
    TOKEN_RING = "TOKEN_RING"
    SHARD_KEY = "SHARD_KEY"
    TOPIC_PARTITIONS = "TOPIC_PARTITIONS"
    DIRECTORY_PREFIX = "DIRECTORY_PREFIX"


@dataclass(frozen=True)
class PartitionBoundFacts:
    """Discovered boundary expressions and metrics for a single partition."""
    partition_name: str
    strategy: PartitionStrategy
    lower_bound: Optional[str] = None
    upper_bound: Optional[str] = None
    partition_ordinal: int = 1
    estimated_rows: Optional[int] = None
    estimated_bytes: Optional[int] = None
    properties: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))

    def __post_init__(self) -> None:
        if not isinstance(self.properties, MappingProxyType):
            object.__setattr__(self, "properties", MappingProxyType(dict(self.properties)))

    def to_dict(self) -> dict[str, Any]:
        return {
            "partition_name": self.partition_name,
            "strategy": self.strategy.value,
            "lower_bound": self.lower_bound,
            "upper_bound": self.upper_bound,
            "partition_ordinal": self.partition_ordinal,
            "estimated_rows": self.estimated_rows,
            "estimated_bytes": self.estimated_bytes,
            "properties": dict(self.properties),
        }


@dataclass(frozen=True)
class SubpartitionFacts:
    """Discovered two-level subpartition details (e.g. Range-Hash in Oracle)."""
    subpartition_name: str
    parent_partition_name: str
    strategy: PartitionStrategy
    bound_value: Optional[str] = None
    estimated_rows: Optional[int] = None
    estimated_bytes: Optional[int] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "subpartition_name": self.subpartition_name,
            "parent_partition_name": self.parent_partition_name,
            "strategy": self.strategy.value,
            "bound_value": self.bound_value,
            "estimated_rows": self.estimated_rows,
            "estimated_bytes": self.estimated_bytes,
        }


@dataclass(frozen=True)
class TokenRangeFacts:
    """Discovered token ring range for distributed databases (Cassandra/Scylla)."""
    start_token: str
    end_token: str
    endpoint_replicas: Tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not isinstance(self.endpoint_replicas, tuple):
            object.__setattr__(self, "endpoint_replicas", tuple(self.endpoint_replicas))

    def to_dict(self) -> dict[str, Any]:
        return {
            "start_token": self.start_token,
            "end_token": self.end_token,
            "endpoint_replicas": list(self.endpoint_replicas),
        }


@dataclass(frozen=True)
class PartitionFacts:
    """Complete physical partitioning specification for a table or dataset."""
    table_name: str
    schema_name: str = "public"
    strategy: PartitionStrategy = PartitionStrategy.NONE
    key_columns: Tuple[str, ...] = field(default_factory=tuple)
    partitions: Tuple[PartitionBoundFacts, ...] = field(default_factory=tuple)
    subpartitions: Tuple[SubpartitionFacts, ...] = field(default_factory=tuple)
    token_ranges: Tuple[TokenRangeFacts, ...] = field(default_factory=tuple)
    shard_keys: Tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        for attr in ("key_columns", "partitions", "subpartitions", "token_ranges", "shard_keys"):
            val = getattr(self, attr)
            if not isinstance(val, tuple):
                object.__setattr__(self, attr, tuple(val))

    def to_dict(self) -> dict[str, Any]:
        return {
            "table_name": self.table_name,
            "schema_name": self.schema_name,
            "strategy": self.strategy.value,
            "key_columns": list(self.key_columns),
            "partitions": [p.to_dict() for p in self.partitions],
            "subpartitions": [sp.to_dict() for sp in self.subpartitions],
            "token_ranges": [tr.to_dict() for tr in self.token_ranges],
            "shard_keys": list(self.shard_keys),
        }
