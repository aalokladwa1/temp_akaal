"""
AKAAL Engine Multiprocess Worker Scheduler Module
==================================================
Implements the Multiprocess Worker Model using standard ProcessPoolExecutor
with process-local database connection handles and SQLite WAL state tracking.
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
from akaal.engine.state import EngineStateRepository
from akaal.engine.checkpoint import CheckpointStore
from akaal.engine.reader import OracleSourceReader
from akaal.engine.writer import PostgreSQLTargetWriter

logger = logging.getLogger("akaal.engine.scheduler")


def worker_process_partition_task(
    partition_dict: Dict[str, Any],
    source_params: Dict[str, Any],
    target_params: Dict[str, Any],
    migration_id: str,
    db_path_state: str,
    db_path_checkpoint: str,
    worker_id: str,
) -> Dict[str, Any]:
    """
    Isolated worker process execution function.
    Opens process-local Oracle reader and PostgreSQL writer instances.
    """
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

    state_repo = EngineStateRepository(db_path=db_path_state)
    checkpoint_store = CheckpointStore(db_path=db_path_checkpoint)

    # Check for existing checkpoint to resume
    latest_ckpt = checkpoint_store.get_latest_checkpoint(partition.partition_id)
    last_key = latest_ckpt["last_committed_key"] if latest_ckpt else None
    committed_rows = latest_ckpt["rows_processed"] if latest_ckpt else 0

    state_repo.set_partition_state(
        partition_id=partition.partition_id,
        migration_id=migration_id,
        table_name=partition.table_name,
        schema_name=partition.schema_name,
        strategy=partition.strategy.value,
        state=PartitionState.IN_PROGRESS,
        lower_bound=partition.lower_bound,
        upper_bound=partition.upper_bound,
        last_committed_source_key=last_key,
        committed_rows=committed_rows,
    )

    from akaal.core.state.state_store import CentralStateStore
    from akaal.events.bus import EnterpriseEventBus
    import datetime

    state_store = CentralStateStore()
    state_store.update_progress(migration_id, {
        "migration_id": migration_id,
        "current_table": f"{partition.schema_name}.{partition.table_name}",
        "status": "RUNNING"
    })

    bus = EnterpriseEventBus()
    bus.publish("migration.progress", {
        "category": "TRANSPORT",
        "severity": "INFO",
        "workerName": worker_id,
        "database": target_params.get("database", "pg_analytics"),
        "schema": partition.schema_name,
        "object": partition.table_name,
        "message": f"Worker {worker_id} streaming {partition.schema_name}.{partition.table_name} batch",
        "timestamp": datetime.datetime.now().strftime("%H:%M:%S")
    })

    reader = OracleSourceReader(source_params)
    writer = PostgreSQLTargetWriter(target_params)

    try:
        reader.open_partition(partition, last_committed_key=last_key)

        total_rows_this_run = 0
        batch_num = latest_ckpt["batch_number"] if latest_ckpt else 0

        while True:
            # Check for cancellation
            m_state = state_repo.get_migration_state(migration_id)
            if m_state and m_state.get("state") in (MigrationState.CANCEL_REQUESTED.value, MigrationState.CANCELLED.value):
                writer.rollback()
                state_repo.set_partition_state(
                    partition_id=partition.partition_id,
                    migration_id=migration_id,
                    table_name=partition.table_name,
                    schema_name=partition.schema_name,
                    strategy=partition.strategy.value,
                    state=PartitionState.PAUSED,
                    committed_rows=committed_rows + total_rows_this_run,
                )
                return {"partition_id": partition.partition_id, "status": "CANCELLED", "rows": total_rows_this_run}

            batch_data, batch_meta = reader.read_batch(partition.batch_size)
            if not batch_data:
                break

            batch_num += 1
            ckpt_id = f"ckpt-{partition.partition_id}-b{batch_num}"
            checkpoint_store.begin_batch(ckpt_id, migration_id, partition.partition_id, partition.table_name, batch_num, worker_id)

            cols = [c[0] for c in reader.cols_info]
            written = writer.write_batch(
                table_name=partition.table_name,
                columns=cols,
                data=batch_data,
                batch_meta=batch_meta,
                pk_columns=partition.pk_columns,
                target_schema=partition.target_schema,
                page_size=5000,
                allow_merge=True,
            )

            writer.commit()

            b_hash = hashlib.sha256(f"{partition.partition_id}:{batch_num}:{written}:{batch_meta.last_pk}".encode()).hexdigest()
            checkpoint_store.mark_batch_committed(
                checkpoint_id=ckpt_id,
                migration_id=migration_id,
                partition_id=partition.partition_id,
                table_name=partition.table_name,
                batch_number=batch_num,
                worker_id=worker_id,
                rows_processed=committed_rows + total_rows_this_run + written,
                last_committed_key=batch_meta.last_pk,
                checksum=b_hash,
            )

            total_rows_this_run += written
            state_repo.set_partition_state(
                partition_id=partition.partition_id,
                migration_id=migration_id,
                table_name=partition.table_name,
                schema_name=partition.schema_name,
                strategy=partition.strategy.value,
                state=PartitionState.IN_PROGRESS,
                last_committed_source_key=batch_meta.last_pk,
                committed_rows=committed_rows + total_rows_this_run,
                last_batch_id=ckpt_id,
            )

        state_repo.set_partition_state(
            partition_id=partition.partition_id,
            migration_id=migration_id,
            table_name=partition.table_name,
            schema_name=partition.schema_name,
            strategy=partition.strategy.value,
            state=PartitionState.COMMITTED,
            committed_rows=committed_rows + total_rows_this_run,
        )

        return {"partition_id": partition.partition_id, "status": "COMPLETED", "rows": total_rows_this_run}

    except Exception as ex:
        writer.rollback()
        state_repo.set_partition_state(
            partition_id=partition.partition_id,
            migration_id=migration_id,
            table_name=partition.table_name,
            schema_name=partition.schema_name,
            strategy=partition.strategy.value,
            state=PartitionState.FAILED,
        )
        raise ex
    finally:
        reader.close()
        writer.close()


class MigrationScheduler:
    """Orchestrates Multiprocess Worker Pool execution over TransportPartition tasks."""

    def __init__(self, spec: MigrationSpecification, source_params: Dict[str, Any], target_params: Dict[str, Any]):
        self.spec = spec
        self.source_params = source_params
        self.target_params = target_params
        self.state_repo = EngineStateRepository()
        self.checkpoint_store = CheckpointStore()

    def execute_partitions(self, partitions: List[TransportPartition]) -> Dict[str, Any]:
        max_workers = max(1, self.spec.tuning_policy.parallelism)
        logger.info(f"[SCHEDULER] Spawning Multiprocess Worker Pool (Max Workers: {max_workers}) for {len(partitions)} partitions...")

        self.state_repo.set_migration_state(self.spec.migration_id, MigrationState.RUNNING)
        total_rows_migrated = 0

        partition_dicts = []
        for p in partitions:
            partition_dicts.append({
                "partition_id": p.partition_id,
                "table_name": p.table_name,
                "schema_name": p.schema_name,
                "target_schema": p.target_schema,
                "strategy": p.strategy,
                "lower_bound": p.lower_bound,
                "upper_bound": p.upper_bound,
                "estimated_rows": p.estimated_rows,
                "batch_size": p.batch_size,
                "pk_columns": p.pk_columns,
            })

        db_path_state = self.state_repo.db_path
        db_path_checkpoint = self.checkpoint_store.db_path

        t_start = time.time()
        from akaal.core.state.state_store import CentralStateStore
        state_store = CentralStateStore()

        from concurrent.futures import ThreadPoolExecutor
        try:
            from concurrent.futures.process import BrokenProcessPool
        except ImportError:
            try:
                from concurrent.futures import BrokenExecutor as BrokenProcessPool
            except ImportError:
                class BrokenProcessPool(Exception): pass

        try:
            with ProcessPoolExecutor(max_workers=max_workers) as executor:
                future_to_part = {
                    executor.submit(
                        worker_process_partition_task,
                        p_dict,
                        self.source_params,
                        self.target_params,
                        self.spec.migration_id,
                        db_path_state,
                        db_path_checkpoint,
                        f"worker-{idx+1}",
                    ): p_dict["partition_id"]
                    for idx, p_dict in enumerate(partition_dicts)
                }

                for idx, future in enumerate(as_completed(future_to_part), 1):
                    part_id = future_to_part[future]
                    try:
                        res = future.result()
                        total_rows_migrated += res.get("rows", 0)
                        elapsed = max(time.time() - t_start, 0.1)
                        tp_mbps = round(total_rows_migrated / elapsed, 2)

                        state_store.update_progress(self.spec.migration_id, {
                            "migration_id": self.spec.migration_id,
                            "rows_migrated": total_rows_migrated,
                            "rows_total": max(total_rows_migrated, len(partition_dicts) * 10),
                            "throughput_mbps": tp_mbps,
                            "rows_per_sec": int(total_rows_migrated / elapsed),
                            "completed_tables": idx,
                            "total_tables": len(partition_dicts),
                            "active_workers": max_workers,
                            "current_table": f"{res.get('schema_name') or ''}.{res.get('table_name', part_id)}".strip('.'),
                            "status": "RUNNING"
                        })
                        logger.info(f"[SCHEDULER] Partition {part_id} completed successfully ({res.get('rows', 0)} rows)")
                    except Exception as ex:
                        logger.error(f"[SCHEDULER] Partition {part_id} failed: {ex}")
                        self.state_repo.set_migration_state(self.spec.migration_id, MigrationState.FAILED)
                        raise ex
        except (BrokenProcessPool, OSError) as mem_err:
            logger.warning(f"[SCHEDULER] Multiprocess Pool hit OS memory limits ({mem_err}). Switching to Adaptive Thread Pool...")
            thread_workers = min(max_workers, 4)
            with ThreadPoolExecutor(max_workers=thread_workers) as thread_executor:
                future_to_part = {
                    thread_executor.submit(
                        worker_process_partition_task,
                        p_dict,
                        self.source_params,
                        self.target_params,
                        self.spec.migration_id,
                        db_path_state,
                        db_path_checkpoint,
                        f"worker-{idx+1}",
                    ): p_dict["partition_id"]
                    for idx, p_dict in enumerate(partition_dicts)
                }

                for idx, future in enumerate(as_completed(future_to_part), 1):
                    part_id = future_to_part[future]
                    try:
                        res = future.result()
                        total_rows_migrated += res.get("rows", 0)
                        elapsed = max(time.time() - t_start, 0.1)
                        tp_mbps = round(total_rows_migrated / elapsed, 2)

                        state_store.update_progress(self.spec.migration_id, {
                            "migration_id": self.spec.migration_id,
                            "rows_migrated": total_rows_migrated,
                            "rows_total": max(total_rows_migrated, len(partition_dicts) * 10),
                            "throughput_mbps": tp_mbps,
                            "rows_per_sec": int(total_rows_migrated / elapsed),
                            "completed_tables": idx,
                            "total_tables": len(partition_dicts),
                            "active_workers": thread_workers,
                            "current_table": res.get("table_name", part_id),
                            "status": "RUNNING"
                        })
                        logger.info(f"[SCHEDULER] Partition {part_id} completed successfully ({res.get('rows', 0)} rows)")
                    except Exception as ex:
                        logger.error(f"[SCHEDULER] Partition {part_id} failed: {ex}")
                        self.state_repo.set_migration_state(self.spec.migration_id, MigrationState.FAILED)
                        raise ex

        return {"status": "SUCCESS", "total_rows": total_rows_migrated}
