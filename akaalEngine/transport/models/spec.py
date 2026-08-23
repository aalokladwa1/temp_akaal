"""
akaalEngine.transport.models.spec
==================================
Partition specs and tuning options.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, List, Optional, Sequence


class PartitionStrategy(str, Enum):
    PK_NUMERIC_RANGE = "PK_NUMERIC_RANGE"
    TEMPORAL_RANGE = "TEMPORAL_RANGE"
    DECIMAL_RANGE = "DECIMAL_RANGE"
    ORACLE_ROWID_RANGE = "ORACLE_ROWID_RANGE"
    NULL_PARTITION = "NULL_PARTITION"
    SINGLE_PARTITION = "SINGLE_PARTITION"


@dataclass(frozen=True)
class TransportPartition:
    """Descriptor for a data transport partition chunk."""
    partition_id: str
    table_name: str
    schema_name: str
    target_schema: str
    strategy: PartitionStrategy
    pk_columns: Sequence[str] = field(default_factory=tuple)
    lower_bound: Optional[Any] = None
    upper_bound: Optional[Any] = None
    is_null_partition: bool = False


@dataclass(frozen=True)
class TransportTuningPolicy:
    """Tuning policy parameters for batch sizing, concurrency, and bandwidth."""
    parallelism: int = 4
    target_batch_bytes: int = 16 * 1024 * 1024  # 16MB
    min_rows_per_batch: int = 100
    max_rows_per_batch: int = 50000
    bandwidth_limit_bytes_sec: int = 0  # 0 = unlimited
    max_queue_batches: int = 10
    max_queue_rows: int = 50000
    max_queue_bytes: int = 64 * 1024 * 1024  # 64MB
    drain_timeout_sec: float = 30.0
