"""
AKAAL Engine Partitioner Module
================================
Generates TransportPartition objects from catalog metadata supporting
inter-table and intra-table Primary Key range partitioning.
"""

import math
import logging
from typing import Dict, Any, List, Optional
from akaal.engine.spec import TransportPartition, PartitionStrategy, TuningPolicy

logger = logging.getLogger("akaal.engine.partitioner")


class TransportPartitioner:
    """Generates TransportPartition objects for inter-table and intra-table parallelism."""

    def __init__(self, tuning_policy: Optional[TuningPolicy] = None):
        self.tuning_policy = tuning_policy or TuningPolicy()

    def generate_partitions_for_table(
        self,
        table_name: str,
        schema_name: str,
        target_schema: str,
        total_rows: int,
        pk_columns: List[str],
        min_pk: Optional[int] = None,
        max_pk: Optional[int] = None,
        strategy: PartitionStrategy = PartitionStrategy.PK_NUMERIC_RANGE,
    ) -> List[TransportPartition]:
        partitions = []
        target_workers = max(1, self.tuning_policy.parallelism)

        # Large tables with numeric PK: split intra-table across worker count
        if (
            strategy == PartitionStrategy.PK_NUMERIC_RANGE
            and min_pk is not None
            and max_pk is not None
            and total_rows > 100000
            and target_workers > 1
        ):
            pk_range = max_pk - min_pk + 1
            step = math.ceil(pk_range / target_workers)

            for i in range(target_workers):
                l_bound = min_pk + (i * step)
                u_bound = min_pk + ((i + 1) * step) if i < target_workers - 1 else max_pk + 1
                if l_bound >= max_pk + 1:
                    break

                part_id = f"part-{table_name}-{i+1:03d}"
                partitions.append(
                    TransportPartition(
                        partition_id=part_id,
                        table_name=table_name,
                        schema_name=schema_name,
                        target_schema=target_schema,
                        strategy=PartitionStrategy.PK_NUMERIC_RANGE,
                        lower_bound=l_bound,
                        upper_bound=u_bound,
                        estimated_rows=math.ceil(total_rows / target_workers),
                        batch_size=self.tuning_policy.batch_size,
                        pk_columns=pk_columns,
                    )
                )

            logger.info(f"[PARTITIONER] Created {len(partitions)} intra-table partitions for {table_name} (Range: {min_pk}..{max_pk})")

        else:
            # Single-stream partition fallback
            part_id = f"part-{table_name}-001"
            partitions.append(
                TransportPartition(
                    partition_id=part_id,
                    table_name=table_name,
                    schema_name=schema_name,
                    target_schema=target_schema,
                    strategy=strategy,
                    lower_bound=min_pk,
                    upper_bound=max_pk,
                    estimated_rows=total_rows,
                    batch_size=self.tuning_policy.batch_size,
                    pk_columns=pk_columns,
                )
            )

        return partitions
