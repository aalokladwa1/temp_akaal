"""
akaalEngine.transport.models.batch
===================================
TransportBatch and BatchMetadata dataclasses.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple


@dataclass(frozen=True)
class TransportBatchMetadata:
    """Metadata header for a transport batch."""
    batch_id: str
    partition_id: str
    table_name: str
    schema_name: str
    sequence_number: int
    row_count: int
    size_bytes: int
    checksum: Optional[str] = None
    checksum_scope: Optional[str] = None


@dataclass
class TransportBatch:
    """Batch payload container passing between SourceReader, Data Processing, and TargetWriter."""
    metadata: TransportBatchMetadata
    rows: List[Mapping[str, Any]]
    column_names: List[str]
    raw_tuples: Optional[List[Tuple[Any, ...]]] = None
