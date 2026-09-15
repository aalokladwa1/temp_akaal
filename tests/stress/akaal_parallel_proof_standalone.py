"""
AKAAL FINAL THREE-METRIC ACCEPTANCE TEST -- RESULT 1 evidence script.

NEW, ADDITIVE, TEST-ONLY script (not part of any existing test suite; not
collected by pytest -- invoke directly with
`.venv/Scripts/python.exe tests/stress/akaal_parallel_proof_standalone.py`).

Purpose: attempt a genuine multi-worker (max_workers>1), multi-partition
(>1) migration run using the REAL canonical
`akaal.replication.scheduling.parallel_scheduler.ParallelReplicationScheduler`
and `akaal.replication.partitioning.range_partitioner.RangePartitioner`
directly against the real SQLite estate
(tests/fixtures/estate/data/source_baseline.sqlite), per
AKAAL_FINAL_THREE_METRIC_TEST_HANDOFF.md SECTION 3/5/20.

Zero production code is modified by this file. The only "new" code is:
  (a) two new IPhysicalReader/IPhysicalWriter-conformant adapter classes for
      the SQLITE_PARALLEL_PROOF system_type, registered via the EXISTING,
      already-public `register_physical_reader`/`register_physical_writer`
      extension-point functions in `akaal.replication.resolver` (not editing
      that file -- calling its documented public API, the same way any real
      new-dialect connector would be plugged in);
  (b) test-fixture setup (building a bare target schema for the chosen
      tables) and independent verification code.

IMPORTANT WINDOWS MULTIPROCESSING NOTE: `ParallelReplicationScheduler`
hardcodes `ProcessPoolExecutor(max_workers=...)` with no `initializer`
argument, and each worker calls the REAL, unmodified
`worker_process_partition_task_canonical` function (imported by reference,
not by value, into the spawned child). On Windows, `multiprocessing` uses
the 'spawn' start method, which re-executes this launching script's
top-level module code in every child process (as `__mp_main__`) BEFORE
running the submitted task. That is why the adapter class definitions and
the `register_physical_reader`/`register_physical_writer` calls below are
placed at plain module level, outside any `if __name__ == "__main__":`
guard -- this is what makes the SQLITE_PARALLEL_PROOF system_type visible
inside each real OS worker process too, without touching any production
file. This script must be launched directly (not via pytest) for that
re-execution behavior to occur.
"""
from __future__ import annotations

import json
import os
import shutil
import sqlite3
import sys
import time
import traceback

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from akaal.replication.contracts import IPhysicalReader, IPhysicalWriter, ConnectorCapability  # noqa: E402
from akaal.replication.resolver import register_physical_reader, register_physical_writer  # noqa: E402
from akaal.engine.spec import TransportPartition, BatchMetadata, PartitionStrategy, TuningPolicy  # noqa: E402

SOURCE_BASELINE = os.path.join(REPO_ROOT, "tests", "fixtures", "estate", "data", "source_baseline.sqlite")
EVIDENCE_DIR = os.path.join(REPO_ROOT, "tests", "fixtures", "estate", "data", "modes", "_parallel_proof_evidence")

SYSTEM_TYPE = "SQLITE_PARALLEL_PROOF"

# Four distinct, real, populated tables -- each becomes exactly one
# TransportPartition (SINGLE_STREAM), so N tables => N disjoint partitions
# by construction (different tables cannot overlap), fed to
# ParallelReplicationScheduler(max_workers=4) for genuine concurrent
# multi-process execution. See the report for why real intra-table
# PK_NUMERIC_RANGE splitting is not reachable with this real dataset
# (RangePartitioner requires total_rows > 100000; the largest real table in
# the estate has 45,816 rows).
CHOSEN_TABLES = [
    "COMMERCE_ORDERS__order_lines",
    "IDENTITY_ACCESS_MGMT__users",
    "FINANCIAL_LEDGER__journal_lines",
    "AUDIT_COMPLIANCE__audit_events",
]


class SQLiteProofPhysicalReader(IPhysicalReader):
    """New, test-only IPhysicalReader implementation for SQLITE_PARALLEL_PROOF.
    Implements the existing production `IPhysicalReader` contract; does not
    modify it."""

    def __init__(self, connection_params):
        self.params = connection_params
        self.conn = None
        self.cursor = None
        self.partition = None
        self.batch_sequence = 0
        self.cols_info = []

    def open_partition(self, partition: TransportPartition, last_committed_key=None) -> None:
        self.partition = partition
        self.batch_sequence = 0
        db_path = self.params["database_name"]
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        table = partition.table_name
        sql = f'SELECT * FROM "{table}"'
        if partition.pk_columns and last_committed_key is not None:
            pk_col = partition.pk_columns[0]
            sql += f' WHERE "{pk_col}" > ? ORDER BY "{pk_col}" ASC'
            self.cursor.execute(sql, (last_committed_key,))
        else:
            self.cursor.execute(sql)
        self.cols_info = [d[0] for d in self.cursor.description]

    def read_batch(self, batch_size: int):
        rows = self.cursor.fetchmany(batch_size)
        self.batch_sequence += 1
        first_key = None
        last_key = None
        if rows and self.partition and self.partition.pk_columns:
            pk_idx = self.cols_info.index(self.partition.pk_columns[0])
            first_key = rows[0][pk_idx]
            last_key = rows[-1][pk_idx]
        meta = BatchMetadata(
            batch_id=f"batch-{self.partition.partition_id}-{self.batch_sequence:06d}",
            partition_id=self.partition.partition_id,
            table_name=self.partition.table_name,
            sequence=self.batch_sequence,
            row_count=len(rows),
            first_pk=first_key,
            last_pk=last_key,
        )
        return rows, meta

    def close(self) -> None:
        if self.cursor:
            try:
                self.cursor.close()
            except Exception:
                pass
        if self.conn:
            try:
                self.conn.close()
            except Exception:
                pass

    def get_capabilities(self) -> ConnectorCapability:
        return ConnectorCapability(can_read=True, can_write=False)


class SQLiteProofPhysicalWriter(IPhysicalWriter):
    """New, test-only IPhysicalWriter implementation for SQLITE_PARALLEL_PROOF.
    Implements the existing production `IPhysicalWriter` contract; does not
    modify it."""

    def __init__(self, connection_params):
        self.params = connection_params
        db_path = self.params["database_name"]
        self.conn = sqlite3.connect(db_path)

    def write_batch(self, table_name, columns, data, batch_meta, pk_columns=None,
                     target_schema="public", page_size=5000, allow_merge=True) -> int:
        if not data:
            return 0
        placeholders = ",".join(["?"] * len(columns))
        col_list = ",".join(f'"{c}"' for c in columns)
        if pk_columns and allow_merge:
            sql = f'INSERT OR REPLACE INTO "{table_name}" ({col_list}) VALUES ({placeholders})'
        else:
            sql = f'INSERT INTO "{table_name}" ({col_list}) VALUES ({placeholders})'
        cur = self.conn.cursor()
        cur.executemany(sql, data)
        return cur.rowcount if cur.rowcount is not None and cur.rowcount >= 0 else len(data)

    def commit(self) -> None:
        self.conn.commit()

    def rollback(self) -> None:
        self.conn.rollback()

    def close(self) -> None:
        try:
            self.conn.close()
        except Exception:
            pass

    def get_capabilities(self) -> ConnectorCapability:
        return ConnectorCapability(can_read=False, can_write=True)


# Module-level registration (runs in the parent AND, on Windows spawn, is
# re-executed in every child worker process because this script is the
# `__main__`/`__mp_main__` module) -- calls only the existing, already-public
# `register_physical_reader`/`register_physical_writer` extension points.
register_physical_reader(SYSTEM_TYPE, SQLiteProofPhysicalReader)
register_physical_writer(SYSTEM_TYPE, SQLiteProofPhysicalWriter)


def _source_row_count(table):
    conn = sqlite3.connect(SOURCE_BASELINE)
    try:
        return conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
    finally:
        conn.close()


def _target_row_count(db_path, table):
    conn = sqlite3.connect(db_path)
    try:
        return conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
    finally:
        conn.close()


def _build_target_schema(target_path, tables):
    """Test-fixture-only setup: create bare target tables (columns + PK,
    no FKs/uniques) for the chosen tables, derived from the real source
    schema via PRAGMA table_info. Not a production migration step -- this
    isolates the parallel data-transport primitive itself, matching how
    `DataTransportStep` in migration_steps.py assumes schema is already
    deployed before it runs."""
    src = sqlite3.connect(SOURCE_BASELINE)
    tgt = sqlite3.connect(target_path)
    try:
        for t in tables:
            cols = src.execute(f'PRAGMA table_info("{t}")').fetchall()
            col_defs = []
            pk_cols = []
            for cid, name, ctype, notnull, dflt, pk in cols:
                col_defs.append(f'"{name}" {ctype}')
                if pk > 0:
                    pk_cols.append((pk, name))
            ddl = f'CREATE TABLE "{t}" ({", ".join(col_defs)}'
            if pk_cols:
                pk_cols.sort()
                ddl += ", PRIMARY KEY (" + ", ".join(f'"{n}"' for _, n in pk_cols) + ")"
            ddl += ")"
            tgt.execute(ddl)
        tgt.commit()
    finally:
        src.close()
        tgt.close()


def _pk_columns_for(table):
    conn = sqlite3.connect(SOURCE_BASELINE)
    try:
        cols = conn.execute(f'PRAGMA table_info("{table}")').fetchall()
        pk = [(c[5], c[1]) for c in cols if c[5] > 0]
        pk.sort()
        return [name for _, name in pk]
    finally:
        conn.close()


def main():
    from akaal.replication.scheduling.parallel_scheduler import ParallelReplicationScheduler
    from akaal.replication.partitioning.range_partitioner import RangePartitioner
    from akaal.replication.checkpointing.checkpoint_store import CheckpointStore

    os.makedirs(EVIDENCE_DIR, exist_ok=True)
    run_id = f"parallel-proof-{int(time.time())}"
    target_path = os.path.join(EVIDENCE_DIR, f"target_{run_id}.sqlite")
    checkpoint_db = os.path.join(EVIDENCE_DIR, f"checkpoints_{run_id}.db")
    state_db = os.path.join(EVIDENCE_DIR, f"state_{run_id}.db")

    evidence = {
        "run_id": run_id,
        "chosen_tables": CHOSEN_TABLES,
        "source_row_counts": {},
        "target_row_counts_before": {},
        "target_row_counts_after": {},
        "max_workers_requested": 4,
        "partitions": [],
        "outcome": None,
        "error": None,
        "traceback": None,
        "elapsed_seconds": None,
        "checkpoint_evidence": [],
    }

    for t in CHOSEN_TABLES:
        evidence["source_row_counts"][t] = _source_row_count(t)

    _build_target_schema(target_path, CHOSEN_TABLES)
    for t in CHOSEN_TABLES:
        evidence["target_row_counts_before"][t] = _target_row_count(target_path, t)

    partitioner = RangePartitioner(tuning_policy=TuningPolicy(parallelism=4))
    partitions = []
    for t in CHOSEN_TABLES:
        pk_cols = _pk_columns_for(t)
        parts = partitioner.generate_partitions_for_table(
            table_name=t,
            schema_name="estate",
            target_schema="estate",
            total_rows=evidence["source_row_counts"][t],
            pk_columns=pk_cols,
            strategy=PartitionStrategy.SINGLE_STREAM,
        )
        partitions.extend(parts)

    evidence["partitions"] = [
        {"partition_id": p.partition_id, "table_name": p.table_name,
         "strategy": str(p.strategy), "estimated_rows": p.estimated_rows,
         "pk_columns": p.pk_columns}
        for p in partitions
    ]
    evidence["partition_count"] = len(partitions)

    source_params = {"system_type": SYSTEM_TYPE, "database_name": SOURCE_BASELINE}
    target_params = {"system_type": SYSTEM_TYPE, "database_name": target_path}

    scheduler = ParallelReplicationScheduler(max_workers=4)

    t0 = time.perf_counter()
    try:
        result = scheduler.execute_partitions(
            partitions=partitions,
            source_params=source_params,
            target_params=target_params,
            migration_id=run_id,
            db_path_state=state_db,
            db_path_checkpoint=checkpoint_db,
        )
        t1 = time.perf_counter()
        evidence["elapsed_seconds"] = t1 - t0
        evidence["outcome"] = "COMPLETED"
        evidence["scheduler_result"] = result
    except Exception as exc:
        t1 = time.perf_counter()
        evidence["elapsed_seconds"] = t1 - t0
        evidence["outcome"] = "EXCEPTION"
        evidence["error"] = f"{type(exc).__name__}: {exc}"
        evidence["traceback"] = traceback.format_exc()

    for t in CHOSEN_TABLES:
        try:
            evidence["target_row_counts_after"][t] = _target_row_count(target_path, t)
        except Exception as e:
            evidence["target_row_counts_after"][t] = f"ERROR: {e}"

    # Independent checkpoint re-query (not from scheduler's own return value)
    if os.path.exists(checkpoint_db):
        try:
            conn = sqlite3.connect(checkpoint_db)
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM checkpoints ORDER BY partition_id, batch_number").fetchall()
            evidence["checkpoint_evidence"] = [dict(r) for r in rows]
            conn.close()
        except Exception as e:
            evidence["checkpoint_evidence_error"] = str(e)

    evidence_path = os.path.join(EVIDENCE_DIR, f"evidence_{run_id}.json")
    with open(evidence_path, "w") as f:
        json.dump(evidence, f, indent=2, default=str)

    print(json.dumps(evidence, indent=2, default=str))
    print(f"\nEVIDENCE_FILE={evidence_path}")


if __name__ == "__main__":
    main()
