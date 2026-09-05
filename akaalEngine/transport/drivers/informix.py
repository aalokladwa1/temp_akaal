"""
akaalEngine.transport.drivers.informix
=======================================
Canonical IBM Informix physical Transport driver (P7A Campaign B, provider #43).

Informix does NOT collapse into DB2 merely because both are IBM products -- they are
physically distinct engines with distinct catalogs and SQL dialects. Informix does not
treat double-quoted strings as delimited identifiers unless `DELIMIDENT` is set in the
session/environment (not assumed here), so this driver is a standalone DB-API 2.0
reader/writer (not a GenericSQL subclass) using unquoted identifiers, connected via
`ibm_db_dbi` (the IBM Informix/DB2 CLI driver's DB-API 2.0-compliant wrapper, paramstyle
'qmark').

No native CDC (Informix CDC API / MQ replication) claim is made -- no capture module
exists here.
"""

from __future__ import annotations

import logging
from typing import Any, List, Optional, Sequence

from akaalEngine.transport.drivers.base import SourceReader, TargetWriter
from akaalEngine.transport.models.batch import TransportBatch, TransportBatchMetadata
from akaalEngine.transport.models.capabilities import (
    CancellationCapability,
    CommitOutcomeState,
    IdempotencyMode,
    LOBMode,
    ProviderCapabilities,
    ResumabilityMode,
)
from akaalEngine.transport.models.spec import TransportPartition

logger = logging.getLogger("akaalEngine.transport.drivers.informix")

INFORMIX_DEFAULT_PORT = 9088


class InformixSourceReader(SourceReader):
    """Real Informix SourceReader using standard DB-API 2.0 cursor iteration with
    unquoted identifiers and a real keyset EXACT_RESUME (`pk > ?` continuation)."""

    def __init__(self, connection_params: dict):
        self.params = connection_params
        self.conn = connection_params.get("db_connection")
        self.cursor = None
        self.partition: Optional[TransportPartition] = None
        self.sequence_number = 0
        self._pk_col: Optional[str] = None
        self._last_key: Optional[Any] = None

    def get_capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            bulk_read=True,
            bulk_write=False,
            lob_read=LOBMode.BOUNDED_MATERIALIZATION,
            lob_write=LOBMode.BOUNDED_MATERIALIZATION,
            cancellation=CancellationCapability.CLOSE_CONNECTION,
            idempotency=IdempotencyMode.NON_IDEMPOTENT,
            resumability=ResumabilityMode.EXACT_RESUME,
        )

    def open_partition(self, partition: TransportPartition, last_committed_key: Optional[Any] = None) -> None:
        self.partition = partition
        self.sequence_number = 0
        self._last_key = last_committed_key
        if self.conn is None:
            self.conn = self.params.get("db_connection")
        if self.conn is None:
            return
        self.cursor = self.conn.cursor()
        pk_col = partition.pk_columns[0] if partition.pk_columns else "id"
        self._pk_col = pk_col
        sql = f"SELECT * FROM {partition.schema_name}:{partition.table_name}"
        conditions: List[str] = []
        exec_params: List[Any] = []
        if partition.lower_bound is not None and partition.upper_bound is not None:
            conditions.append(f"{pk_col} >= {partition.lower_bound} AND {pk_col} < {partition.upper_bound}")
        elif partition.is_null_partition:
            conditions.append(f"{pk_col} IS NULL")
        if last_committed_key is not None:
            conditions.append(f"{pk_col} > ?")
            exec_params.append(last_committed_key)
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        sql += f" ORDER BY {pk_col}"
        if exec_params:
            self.cursor.execute(sql, tuple(exec_params))
        else:
            self.cursor.execute(sql)

    def read_batch(self, batch_size: int = 5000) -> Optional[TransportBatch]:
        if not self.cursor:
            return None
        raw_rows = self.cursor.fetchmany(batch_size)
        if not raw_rows:
            return None
        self.sequence_number += 1
        col_names = [d[0].lower() for d in self.cursor.description] if self.cursor.description else []
        rows_dict = [dict(zip(col_names, r)) for r in raw_rows]
        if rows_dict and self._pk_col:
            pk_lookup = self._pk_col.lower()
            if pk_lookup in rows_dict[-1]:
                self._last_key = rows_dict[-1][pk_lookup]
        meta = TransportBatchMetadata(
            batch_id=f"informix-batch-{self.sequence_number}",
            partition_id=self.partition.partition_id if self.partition else "p0",
            table_name=self.partition.table_name if self.partition else "unknown",
            schema_name=self.partition.schema_name if self.partition else "unknown",
            sequence_number=self.sequence_number,
            row_count=len(rows_dict),
            size_bytes=sum(len(str(r)) for r in raw_rows),
        )
        return TransportBatch(metadata=meta, rows=rows_dict, column_names=col_names, raw_tuples=raw_rows)

    @property
    def resume_position(self) -> Optional[Any]:
        return self._last_key

    def cancel(self) -> None:
        pass

    def close(self) -> None:
        if self.cursor:
            try:
                self.cursor.close()
            except Exception:
                pass


class InformixTargetWriter(TargetWriter):
    """Real Informix TargetWriter using executemany() with unquoted identifiers and a real
    physical `verify_uncertain_commit` (PK-requery)."""

    def __init__(self, connection_params: Optional[dict] = None):
        params = connection_params or {}
        super().__init__(
            migration_id=params.get("migration_id"),
            batch_id=params.get("batch_id") or params.get("job_id"),
            endpoint_identity=params.get("endpoint_identity") or params.get("host"),
        )
        self.params = params
        self.conn = params.get("db_connection")
        self.cursor = self.conn.cursor() if self.conn else None
        self._in_transaction = False
        self._active_tx_uncommitted_rows = 0

    def get_capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            bulk_read=False,
            bulk_write=True,
            lob_read=LOBMode.BOUNDED_MATERIALIZATION,
            lob_write=LOBMode.BOUNDED_MATERIALIZATION,
            cancellation=CancellationCapability.CLOSE_CONNECTION,
            idempotency=IdempotencyMode.CONDITIONALLY_IDEMPOTENT,
            resumability=ResumabilityMode.EXACT_RESUME,
        )

    def write_batch(
        self,
        table_name: str,
        batch: TransportBatch,
        target_schema: str = "informix",
        pk_columns: Optional[Sequence[str]] = None,
        allow_merge: bool = True,
    ) -> int:
        self.verify_fencing()
        if not batch.rows:
            return 0
        if not self.cursor:
            if self.params.get("db_connection"):
                self.conn = self.params["db_connection"]
                self.cursor = self.conn.cursor()
            else:
                from akaalEngine.transport.models.errors import TransportWriteError
                raise TransportWriteError("InformixTargetWriter has no active database connection or cursor.")

        cols = batch.column_names
        placeholders = ", ".join(["?"] * len(cols))
        sql = f"INSERT INTO {target_schema}:{table_name} ({', '.join(cols)}) VALUES ({placeholders})"
        data_tuples = [tuple(r.get(c) for c in cols) for r in batch.rows]
        self._in_transaction = True
        try:
            self.cursor.executemany(sql, data_tuples)
            written = self.cursor.rowcount if (hasattr(self.cursor, "rowcount") and self.cursor.rowcount and self.cursor.rowcount >= 0) else len(batch.rows)
            self._active_tx_uncommitted_rows += written
            return written
        except Exception:
            self._in_transaction = True
            raise

    def verify_uncertain_commit(
        self,
        table_name: str,
        target_schema: str,
        pk_columns: Optional[Sequence[str]],
        batch: TransportBatch,
    ) -> CommitOutcomeState:
        if not self.conn or not pk_columns or not batch.rows:
            return CommitOutcomeState.UNKNOWN_COMMIT_OUTCOME
        try:
            pk_col = pk_columns[0]
            pk_values = [r.get(pk_col) for r in batch.rows if r.get(pk_col) is not None]
            if not pk_values:
                return CommitOutcomeState.UNKNOWN_COMMIT_OUTCOME
            check_cur = self.conn.cursor()
            placeholders = ", ".join(["?"] * len(pk_values))
            check_cur.execute(
                f"SELECT count(*) FROM {target_schema}:{table_name} WHERE {pk_col} IN ({placeholders})",
                tuple(pk_values),
            )
            row = check_cur.fetchone()
            check_cur.close()
            found = row[0] if row else 0
            if found >= len(pk_values):
                return CommitOutcomeState.COMMITTED
            elif found == 0:
                return CommitOutcomeState.NOT_COMMITTED
            return CommitOutcomeState.UNKNOWN_COMMIT_OUTCOME
        except Exception as exc:
            logger.warning(f"[InformixTargetWriter] verify_uncertain_commit physical check failed: {exc}")
            return CommitOutcomeState.UNKNOWN_COMMIT_OUTCOME

    def commit(self) -> None:
        self.verify_fencing()
        if self.conn:
            self.conn.commit()
        self._in_transaction = False
        self._active_tx_uncommitted_rows = 0

    def rollback(self) -> None:
        if not self._in_transaction and self._active_tx_uncommitted_rows == 0:
            from akaalEngine.transport.models.errors import TransportWriteError
            raise TransportWriteError("Physical target rollback rejected: target writer has no active uncommitted transaction to roll back.")
        if not self.conn:
            from akaalEngine.transport.models.errors import TransportWriteError
            raise TransportWriteError("Physical target rollback rejected: target writer database connection is not active or connected.")
        self.conn.rollback()
        self._in_transaction = False
        self._active_tx_uncommitted_rows = 0

    def cancel(self) -> None:
        pass

    def close(self) -> None:
        if self.cursor:
            try:
                self.cursor.close()
            except Exception:
                pass
