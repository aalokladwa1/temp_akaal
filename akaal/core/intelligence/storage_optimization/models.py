"""
Akaal — Storage Optimization Models
===================================
Defines the immutable structures for tablespace mappings, partition strategies,
and database growth projections.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Tuple


@dataclass(frozen=True)
class TablespaceAllocation:
    """Immutable model representing storage boundary definitions of a tablespace."""
    tablespace_name: str
    datafile_count: int
    initial_extent_kb: int
    next_extent_kb: int
    max_size_kb: int
    autoextend: bool
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PartitionStrategy:
    """Immutable description of partition schemes targeting huge tables."""
    table_name: str
    partition_type: str       # RANGE, LIST, HASH
    partition_key: str
    partition_count: int
    partition_names: Tuple[str, ...]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class StorageProjection:
    """Calculated projections of initial and future physical size allocations."""
    table_name: str
    row_count: int
    avg_row_length_bytes: int
    data_size_kb: int
    index_size_kb: int
    total_size_kb: int
    projected_growth_1yr_kb: int
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class StorageConstraint:
    """Storage limits and parameters defined by target platforms or quotas."""
    max_database_size_kb: int
    max_tablespace_size_kb: int
    block_size_bytes: int
    unsupported_features: Tuple[str, ...]
