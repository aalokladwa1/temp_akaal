"""
akaalEngine.transport.drivers.generic_sql
==========================================
Generic SQL SourceReader and TargetWriter driver for SQLite, MySQL, MSSQL, Db2 with physical fencing verification.
"""

import logging
from typing import Any, Dict, List, Optional

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

logger = logging.getLogger("akaalEngine.transport.drivers.generic_sql")


class GenericSQLSourceReader(SourceReader):
    """Generic SQL SourceReader using standard Python DB-API 2.0 cursor iteration."""

    def __init__(self, connection_params: dict):
        self.params = connection_params
        self.conn = None
        self.cursor = None
        self.partition = None
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
        if self.params.get("db_connection"):
            self.conn = self.params["db_connection"]
            self.cursor = self.conn.cursor()
            pk_col = partition.pk_columns[0] if partition.pk_columns else "id"
            self._pk_col = pk_col
            sql = f'SELECT * FROM "{partition.schema_name}"."{partition.table_name}"'
            conditions: List[str] = []
            exec_params: List[Any] = []
            if partition.lower_bound is not None and partition.upper_bound is not None:
                conditions.append(f'"{pk_col}" >= {partition.lower_bound} AND "{pk_col}" < {partition.upper_bound}')
            elif partition.is_null_partition:
                conditions.append(f'"{pk_col}" IS NULL')
            if last_committed_key is not None:
                # EXACT_RESUME: a fresh process reopening this partition after a crash must
                # continue strictly after the last durably-committed key, not silently
                # re-scan the whole table (which would re-deliver already-written rows and
                # falsify the EXACT_RESUME capability this reader declares above).
                paramstyle = _resolve_paramstyle(self.conn)
                placeholder = _build_placeholder(paramstyle, 1)
                conditions.append(f'"{pk_col}" > {placeholder}')
                exec_params.append(last_committed_key)
            if conditions:
                sql += " WHERE " + " AND ".join(conditions)
            # ORDER BY is required for EXACT_RESUME correctness: fetchmany() pagination and
            # keyset resume both depend on a stable row order across a fresh cursor/connection.
            sql += f' ORDER BY "{pk_col}"'
            if exec_params:
                self.cursor.execute(sql, tuple(exec_params))
            else:
                self.cursor.execute(sql)

    def read_batch(self, batch_size: int = 5000) -> None:
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
            batch_id=f"sql-batch-{self.sequence_number}",
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
        """The last-read row's primary-key value -- persisted by TransportAuthority as the
        checkpoint's read_position, and passed back into open_partition()'s
        last_committed_key on a fresh-process resume."""
        return self._last_key

    def cancel(self) -> None:
        pass

    def close(self) -> None:
        if self.cursor:
            try:
                self.cursor.close()
            except Exception:
                pass


def _resolve_paramstyle(connection: Any) -> str:
    """
    Determines the real DB-API 2.0 paramstyle of a connection's driver module, rather than
    assuming '?' (qmark) -- psycopg2 and PyMySQL both declare 'pyformat'/'format' (%s), not
    qmark, so a hardcoded '?' placeholder silently produces invalid SQL (or a driver-level
    parse error) against any wire-compatible provider using those drivers (PostgreSQL, MySQL,
    MariaDB, CockroachDB, YugabyteDB, TiDB, SingleStore). Falls back to 'qmark' only when the
    driver module cannot be introspected (matches sqlite3's/pyodbc's actual declared style).
    """
    module = type(connection).__module__.split(".")[0] if connection is not None else ""
    try:
        driver_mod = __import__(module) if module else None
        style = getattr(driver_mod, "paramstyle", None)
        if style:
            return style
    except Exception:
        pass
    return "qmark"


def _build_placeholder(paramstyle: str, count: int) -> str:
    if paramstyle in ("format", "pyformat"):
        return ", ".join(["%s"] * count)
    if paramstyle == "numeric":
        return ", ".join(f":{i + 1}" for i in range(count))
    if paramstyle == "named":
        return ", ".join(f":p{i}" for i in range(count))
    return ", ".join(["?"] * count)  # qmark (sqlite3, pyodbc)


class GenericSQLTargetWriter(TargetWriter):
    """Generic SQL TargetWriter using executemany batch insertion with physical mutation fencing.
    Placeholder style is resolved from the connection's driver module (see _resolve_paramstyle),
    not hardcoded -- this is what makes "generic" actually true across DB-API 2.0 drivers."""

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
        self._in_transaction: bool = False
        self._active_tx_uncommitted_rows: int = 0

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
        target_schema: str = "public",
        pk_columns: None = None,
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
                raise TransportWriteError("GenericSQLTargetWriter has no active database connection or cursor.")

        cols = batch.column_names
        paramstyle = _resolve_paramstyle(self.conn)
        placeholders = _build_placeholder(paramstyle, len(cols))
        sql = f'INSERT INTO "{target_schema}"."{table_name}" ({", ".join(cols)}) VALUES ({placeholders})'
        data_tuples = [tuple(r.get(c) for c in cols) for r in batch.rows]
        self._in_transaction = True
        try:
            self.cursor.executemany(sql, data_tuples)
            written = self.cursor.rowcount if (hasattr(self.cursor, "rowcount") and self.cursor.rowcount >= 0) else len(batch.rows)
            self._active_tx_uncommitted_rows += written
            return written
        except Exception:
            self._in_transaction = True
            raise

    def verify_uncertain_commit(
        self,
        table_name: str,
        target_schema: str,
        pk_columns: None,
        batch: TransportBatch,
    ) -> CommitOutcomeState:
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
