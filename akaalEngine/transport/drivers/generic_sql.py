"""
akaalEngine.transport.drivers.generic_sql
==========================================
Generic SQL SourceReader and TargetWriter driver for SQLite, MySQL, MSSQL, Db2.
"""

import logging

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

    def open_partition(self, partition: TransportPartition, last_committed_key: None = None) -> None:
        self.partition = partition
        self.sequence_number = 0
        if self.params.get("db_connection"):
            self.conn = self.params["db_connection"]
            self.cursor = self.conn.cursor()
            pk_col = partition.pk_columns[0] if partition.pk_columns else "id"
            sql = f'SELECT * FROM "{partition.schema_name}"."{partition.table_name}"'
            if partition.lower_bound is not None and partition.upper_bound is not None:
                sql += f' WHERE "{pk_col}" >= {partition.lower_bound} AND "{pk_col}" < {partition.upper_bound}'
            elif partition.is_null_partition:
                sql += f' WHERE "{pk_col}" IS NULL'
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

    def cancel(self) -> None:
        pass

    def close(self) -> None:
        if self.cursor:
            try:
                self.cursor.close()
            except Exception:
                pass


class GenericSQLTargetWriter(TargetWriter):
    """Generic SQL TargetWriter using executemany batch insertion."""

    def __init__(self, connection_params: dict):
        self.params = connection_params
        self.conn = connection_params.get("db_connection")
        self.cursor = self.conn.cursor() if self.conn else None

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
        if not batch.rows:
            return 0
        if not self.cursor and self.params.get("db_connection"):
            self.conn = self.params["db_connection"]
            self.cursor = self.conn.cursor()

        cols = batch.column_names
        placeholders = ", ".join(["?"] * len(cols))
        sql = f'INSERT INTO "{target_schema}"."{table_name}" ({", ".join(cols)}) VALUES ({placeholders})'
        data_tuples = [tuple(r.get(c) for c in cols) for r in batch.rows]
        if self.cursor:
            self.cursor.executemany(sql, data_tuples)
        return len(batch.rows)

    def verify_uncertain_commit(
        self,
        table_name: str,
        target_schema: str,
        pk_columns: None,
        batch: TransportBatch,
    ) -> CommitOutcomeState:
        return CommitOutcomeState.UNKNOWN_COMMIT_OUTCOME

    def commit(self) -> None:
        if self.conn:
            self.conn.commit()

    def rollback(self) -> None:
        if self.conn:
            self.conn.rollback()

    def cancel(self) -> None:
        pass

    def close(self) -> None:
        if self.cursor:
            try:
                self.cursor.close()
            except Exception:
                pass
