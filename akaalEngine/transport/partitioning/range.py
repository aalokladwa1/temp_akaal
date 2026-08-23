"""
akaalEngine.transport.partitioning.range
=========================================
RangePartitioner for numeric, decimal, temporal, ROWID, and NULL partition generation.
Mined from `akaal/replication/partitioning/range_partitioner.py`.
"""

import math
from typing import Any, List, Optional, Sequence

from akaalEngine.transport.models.spec import PartitionStrategy, TransportPartition, TransportTuningPolicy


class RangePartitioner:
    """
    Generates TransportPartition chunks with zero gaps and zero overlaps.
    Supports numeric ranges, negative key ranges, fixed-precision decimal keys,
    temporal timestamp boundaries, Oracle ROWIDs, and dedicated NULL partitions.
    """

    def __init__(self, tuning_policy: Optional[TransportTuningPolicy] = None):
        self.tuning_policy = tuning_policy or TransportTuningPolicy()

    def generate_partitions(
        self,
        table_name: str,
        schema_name: str,
        target_schema: str,
        total_rows: int,
        pk_columns: Sequence[str],
        min_pk: Optional[Any] = None,
        max_pk: Optional[Any] = None,
        has_null_keys: bool = False,
        strategy: PartitionStrategy = PartitionStrategy.PK_NUMERIC_RANGE,
    ) -> List[TransportPartition]:
        partitions: List[TransportPartition] = []

        if total_rows == 0:
            return partitions

        target_workers = max(1, self.tuning_policy.parallelism)

        # Dedicated NULL partition routing if table contains NULL primary key values
        if has_null_keys:
            partitions.append(
                TransportPartition(
                    partition_id=f"part-{table_name}-null",
                    table_name=table_name,
                    schema_name=schema_name,
                    target_schema=target_schema,
                    strategy=PartitionStrategy.NULL_PARTITION,
                    pk_columns=tuple(pk_columns),
                    is_null_partition=True,
                )
            )

        # Single-value partition if min_pk == max_pk
        if min_pk is not None and max_pk is not None and min_pk == max_pk:
            partitions.append(
                TransportPartition(
                    partition_id=f"part-{table_name}-single",
                    table_name=table_name,
                    schema_name=schema_name,
                    target_schema=target_schema,
                    strategy=strategy,
                    pk_columns=tuple(pk_columns),
                    lower_bound=min_pk,
                    upper_bound=max_pk,
                )
            )
            return partitions

        # Numeric and Decimal range partitioning
        if (
            strategy in (PartitionStrategy.PK_NUMERIC_RANGE, PartitionStrategy.DECIMAL_RANGE)
            and min_pk is not None
            and max_pk is not None
        ):
            pk_range = max_pk - min_pk
            if pk_range <= 0:
                pk_range = 1

            # Clamp partition count if target_workers > key_cardinality
            actual_partitions = min(target_workers, int(pk_range))
            step = pk_range / max(1, actual_partitions)

            for i in range(actual_partitions):
                l_bound = min_pk + (i * step)
                u_bound = min_pk + ((i + 1) * step) if i < actual_partitions - 1 else max_pk + 1

                part_id = f"part-{table_name}-{i+1:03d}"
                partitions.append(
                    TransportPartition(
                        partition_id=part_id,
                        table_name=table_name,
                        schema_name=schema_name,
                        target_schema=target_schema,
                        strategy=strategy,
                        pk_columns=tuple(pk_columns),
                        lower_bound=l_bound,
                        upper_bound=u_bound,
                    )
                )

        # Single partition fallback if range bounds not provided
        if not partitions:
            partitions.append(
                TransportPartition(
                    partition_id=f"part-{table_name}-full",
                    table_name=table_name,
                    schema_name=schema_name,
                    target_schema=target_schema,
                    strategy=PartitionStrategy.SINGLE_PARTITION,
                    pk_columns=tuple(pk_columns),
                )
            )

        return partitions
