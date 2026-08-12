"""
AKAAL Replication Engine — Canonical Multiprocess Parallel Scheduler
======================================================================
Multiprocess Worker Scheduler using ProcessPoolExecutor for isolated worker processes.
"""

import time
import hashlib
import logging
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Dict, Any, List, Optional, Tuple

from akaal.engine.spec import (
    MigrationSpecification,
    TransportPartition,
    PartitionState,
    MigrationState,
    BatchMetadata,
)
from akaal.replication.resolver import resolve_physical_reader, resolve_physical_writer
from akaal.replication.checkpointing.checkpoint_store import CheckpointStore
from akaal.core.state.state_store import CentralStateStore

logger = logging.getLogger("akaal.replication.scheduling.parallel_scheduler")


def worker_process_partition_task_canonical(
    partition_dict: Dict[str, Any],
    source_params: Dict[str, Any],
    target_params: Dict[str, Any],
    migration_id: str,
    db_path_state: str,
    db_path_checkpoint: str,
    worker_id: str,
) -> Dict[str, Any]:
    """Isolated process execution function for canonical replication worker task."""
    partition = TransportPartition(
        partition_id=partition_dict["partition_id"],
        table_name=partition_dict["table_name"],
        schema_name=partition_dict["schema_name"],
        target_schema=partition_dict["target_schema"],
        strategy=partition_dict["strategy"],
        lower_bound=partition_dict.get("lower_bound"),
        upper_bound=partition_dict.get("upper_bound"),
        estimated_rows=partition_dict.get("estimated_rows", 0),
        batch_size=partition_dict.get("batch_size", 25000),
        pk_columns=partition_dict.get("pk_columns", []),
    )

    checkpoint_store = CheckpointStore(db_path=db_path_checkpoint)
    latest_ckpt = checkpoint_store.get_latest_checkpoint(partition.partition_id)
    last_key = latest_ckpt["last_committed_key"] if latest_ckpt else None
    committed_rows = latest_ckpt["rows_processed"] if latest_ckpt else 0

    state_store = CentralStateStore()
    state_store.update_progress(migration_id, {
        "migration_id": migration_id,
        "current_table": f"{partition.schema_name}.{partition.table_name}",
        "status": "RUNNING"
    })

    src_sys = source_params.get("system_type", "ORACLE")
    tgt_sys = target_params.get("system_type", "POSTGRESQL")
    reader = resolve_physical_reader(src_sys, source_params)
    writer = resolve_physical_writer(tgt_sys, target_params)

    start_t = time.time()
    total_written = 0
    batch_count = 0

    try:
        reader.open_partition(partition, last_committed_key=last_key)
        batch_size = partition.batch_size or 25000

        while True:
            rows, meta = reader.read_batch(batch_size)
            if not rows:
                break

            batch_number = meta.sequence_number
            checkpoint_id = f"chkpt-{partition.partition_id}-{batch_number:06d}"
            checkpoint_store.begin_batch(
                checkpoint_id=checkpoint_id,
                migration_id=migration_id,
                partition_id=partition.partition_id,
                table_name=partition.table_name,
                batch_number=batch_number,
                worker_id=worker_id,
            )

            written = writer.write_batch(
                table_name=partition.table_name,
                columns=reader.cols_info,
                data=rows,
                batch_meta=meta,
                pk_columns=partition.pk_columns,
                target_schema=partition.target_schema,
                allow_merge=True,
            )
            writer.commit()

            checkpoint_store.mark_batch_committed(
                checkpoint_id=checkpoint_id,
                migration_id=migration_id,
                partition_id=partition.partition_id,
                table_name=partition.table_name,
                batch_number=batch_number,
                worker_id=worker_id,
                rows_processed=written,
                last_committed_key=meta.last_pk,
                checksum=hashlib.sha256(f"{meta.batch_id}:{written}".encode()).hexdigest(),
            )

            total_written += written
            batch_count += 1

            state_store.update_progress(migration_id, {
                "migration_id": migration_id,
                "rows_migrated": committed_rows + total_written,
                "status": "RUNNING"
            })

        duration = max(0.001, time.time() - start_t)
        return {
            "partition_id": partition.partition_id,
            "table_name": partition.table_name,
            "status": "COMPLETED",
            "rows_migrated": total_written,
            "batches_processed": batch_count,
            "duration_sec": duration,
            "throughput_rows_sec": round(total_written / duration, 2),
        }
    except Exception as exc:
        logger.error(f"[CANONICAL WORKER TASK] Failed partition {partition.partition_id}: {exc}", exc_info=True)
        writer.rollback()
        raise exc
    finally:
        reader.close()
        writer.close()


class ParallelReplicationScheduler:
    """Multiprocess Worker Scheduler coordinating execution across worker processes."""

    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers

    def execute_partitions(
        self,
        partitions: List[TransportPartition],
        source_params: Dict[str, Any],
        target_params: Dict[str, Any],
        migration_id: str,
        db_path_state: str = "artifacts/state.db",
        db_path_checkpoint: str = "artifacts/checkpoints.db",
    ) -> Dict[str, Any]:
        start_time = time.time()
        results = []
        total_rows = 0

        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_part = {}
            for i, part in enumerate(partitions):
                part_dict = {
                    "partition_id": part.partition_id,
                    "table_name": part.table_name,
                    "schema_name": part.schema_name,
                    "target_schema": part.target_schema,
                    "strategy": part.strategy,
                    "lower_bound": part.lower_bound,
                    "upper_bound": part.upper_bound,
                    "estimated_rows": part.estimated_rows,
                    "batch_size": part.batch_size,
                    "pk_columns": part.pk_columns,
                }
                worker_id = f"worker-proc-{i % self.max_workers:02d}"
                f = executor.submit(
                    worker_process_partition_task_canonical,
                    part_dict,
                    source_params,
                    target_params,
                    migration_id,
                    db_path_state,
                    db_path_checkpoint,
                    worker_id,
                )
                future_to_part[f] = part.partition_id

            for future in as_completed(future_to_part):
                part_id = future_to_part[future]
                try:
                    res = future.result()
                    results.append(res)
                    total_rows += res.get("rows_migrated", 0)
                except Exception as exc:
                    logger.error(f"[PARALLEL SCHEDULER] Partition {part_id} raised exception: {exc}")
                    raise exc

        total_time = max(0.001, time.time() - start_time)
        return {
            "status": "COMPLETED",
            "migration_id": migration_id,
            "total_rows": total_rows,
            "partitions_completed": len(results),
            "execution_time_sec": round(total_time, 2),
            "throughput_rows_sec": round(total_rows / total_time, 2),
            "partition_results": results,
        }
