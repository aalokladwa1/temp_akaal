"""
akaalEngine.transport.drivers.oracle
=====================================
Canonical High-Performance Oracle SourceReader driver mined from `akaal/engine/reader.py`.
"""

import logging
from typing import Any, Dict, List, Optional, Sequence, Tuple

try:
    import oracledb
    _HAS_ORACLE = True
except ImportError:
    oracledb = None
    _HAS_ORACLE = False

from akaalEngine.transport.drivers.base import SourceReader
from akaalEngine.transport.models.batch import TransportBatch, TransportBatchMetadata
from akaalEngine.transport.models.capabilities import (
    CancellationCapability,
    IdempotencyMode,
    LOBMode,
    ProviderCapabilities,
    ResumabilityMode,
)
from akaalEngine.transport.models.spec import PartitionStrategy, TransportPartition

logger = logging.getLogger("akaalEngine.transport.drivers.oracle")


class OracleSourceReader(SourceReader):
    """
    High-performance Oracle fast-path reader using oracledb streaming cursor
    with outputtypehandler for CLOB/BLOB locators and ROWID/PK range queries.
    Mined from `akaal/engine/reader.py`.
    """

    def __init__(self, connection_params: Dict[str, Any]):
        self.params = connection_params
        self.conn = None
        self.cursor = None
        self.partition: Optional[TransportPartition] = None
        self.sequence_number = 0
        self.cols_info: List[Tuple[str, str]] = []

    def get_capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            bulk_read=True,
            bulk_write=False,
            lob_read=LOBMode.BOUNDED_MATERIALIZATION,
            lob_write=LOBMode.BOUNDED_MATERIALIZATION,
            cancellation=CancellationCapability.NATIVE_CANCEL if _HAS_ORACLE else CancellationCapability.CLOSE_CONNECTION,
            idempotency=IdempotencyMode.NON_IDEMPOTENT,
            resumability=ResumabilityMode.EXACT_RESUME,
        )

    def _output_type_handler(self, cursor, name, default_type=None, size=None, precision=None, scale=None):
        if not _HAS_ORACLE:
            return None
        type_code = default_type if default_type is not None else (name.type_code if hasattr(name, "type_code") else None)
        if type_code == oracledb.DB_TYPE_CLOB:
            return cursor.var(oracledb.DB_TYPE_LONG, arraysize=cursor.arraysize)
        if type_code == oracledb.DB_TYPE_BLOB:
            return cursor.var(oracledb.DB_TYPE_LONG_RAW, arraysize=cursor.arraysize)

    def open_partition(self, partition: TransportPartition, last_committed_key: Optional[Any] = None) -> None:
        self.partition = partition
        self.sequence_number = 0

        if not _HAS_ORACLE or self.params.get("mock_mode"):
            return

        user = self.params.get("username") or self.params.get("user")
        password = self.params.get("password")
        host = self.params.get("host") or "127.0.0.1"
        port = int(self.params.get("port") or 1521)
        database = self.params.get("database") or self.params.get("database_name")

        dsn = f"{host}:{port}/{database}"
        self.conn = oracledb.connect(user=user, password=password, dsn=dsn)
        self.conn.outputtypehandler = self._output_type_handler
        self.cursor = self.conn.cursor()

        t_sch = partition.schema_name or user
        t_name = partition.table_name
        pk_col = partition.pk_columns[0] if partition.pk_columns else "ID"

        sql_clauses = [f'SELECT * FROM "{t_sch}"."{t_name}"']
        binds = {}

        if partition.strategy == PartitionStrategy.PK_NUMERIC_RANGE:
            where_conds = []
            if last_committed_key is not None:
                where_conds.append(f'"{pk_col}" > :last_key')
                binds["last_key"] = last_committed_key
            elif partition.lower_bound is not None:
                where_conds.append(f'"{pk_col}" >= :lower_bound')
                binds["lower_bound"] = partition.lower_bound

            if partition.upper_bound is not None:
                where_conds.append(f'"{pk_col}" < :upper_bound')
                binds["upper_bound"] = partition.upper_bound

            if where_conds:
                sql_clauses.append("WHERE " + " AND ".join(where_conds))
            sql_clauses.append(f'ORDER BY "{pk_col}" ASC')

        elif partition.strategy == PartitionStrategy.ORACLE_ROWID_RANGE:
            if partition.lower_bound and partition.upper_bound:
                sql_clauses.append(f"WHERE ROWID >= '{partition.lower_bound}' AND ROWID < '{partition.upper_bound}'")

        elif partition.strategy == PartitionStrategy.NULL_PARTITION:
            sql_clauses.append(f'WHERE "{pk_col}" IS NULL')

        sql = " ".join(sql_clauses)
        self.cursor.execute(sql, binds)

    def read_batch(self, batch_size: int = 5000) -> Optional[TransportBatch]:
        if not self.cursor:
            return None

        raw_rows = self.cursor.fetchmany(batch_size)
        if not raw_rows:
            return None

        self.sequence_number += 1
        col_names = [d[0].lower() for d in self.cursor.description] if self.cursor.description else []
        rows_dict = [dict(zip(col_names, r)) for r in raw_rows]

        meta = TransportBatchMetadata(
            batch_id=f"ora-batch-{self.sequence_number}",
            partition_id=self.partition.partition_id if self.partition else "p0",
            table_name=self.partition.table_name if self.partition else "unknown",
            schema_name=self.partition.schema_name if self.partition else "unknown",
            sequence_number=self.sequence_number,
            row_count=len(rows_dict),
            size_bytes=sum(len(str(r)) for r in raw_rows),
        )
        return TransportBatch(metadata=meta, rows=rows_dict, column_names=col_names, raw_tuples=raw_rows)

    def cancel(self) -> None:
        if self.conn and _HAS_ORACLE:
            try:
                self.conn.cancel()
            except Exception:
                pass

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
