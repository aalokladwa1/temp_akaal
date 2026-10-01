"""
akaalEngine.transport.drivers.oracle
=====================================
Canonical High-Performance Oracle SourceReader driver mined from `akaal/engine/reader.py`.
"""

import logging
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

try:
    import oracledb
    _HAS_ORACLE = True
except ImportError:
    oracledb = None
    _HAS_ORACLE = False

from akaalEngine.transport.drivers.base import SourceReader, TargetWriter
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

        if not self.conn:
            user = self.params.get("username") or self.params.get("user")
            password = self.params.get("password")
            host = self.params.get("host") or "127.0.0.1"
            port = int(self.params.get("port") or 1521)
            database = self.params.get("database") or self.params.get("database_name") or self.params.get("service_name") or self.params.get("sid") or "FREEPDB1"

            dsn = f"{host}:{port}/{database}"
            self.conn = oracledb.connect(user=user, password=password, dsn=dsn)
            self.conn.outputtypehandler = self._output_type_handler
            self.cursor = self.conn.cursor()
        elif not self.cursor:
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
            self.cursor = None
        if self.conn:
            try:
                self.conn.close()
            except Exception:
                pass
            self.conn = None


class OracleTargetWriter(TargetWriter):
    """
    High-performance Oracle target writer using oracledb batch execution (executemany)
    and physical mutation fencing verification.
    """

    def __init__(self, connection_params: Optional[Dict[str, Any]] = None):
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
            cancellation=CancellationCapability.NATIVE_CANCEL if _HAS_ORACLE else CancellationCapability.CLOSE_CONNECTION,
            idempotency=IdempotencyMode.CONDITIONALLY_IDEMPOTENT,
            resumability=ResumabilityMode.EXACT_RESUME,
        )

    def _connect(self) -> None:
        if self.conn is not None and self.cursor is not None:
            return

        if self.params.get("db_connection"):
            self.conn = self.params["db_connection"]
            self.cursor = self.conn.cursor()
            return

        if not _HAS_ORACLE:
            from akaalEngine.transport.models.errors import TransportCapabilityError
            raise TransportCapabilityError("oracledb library is not installed for OracleTargetWriter driver.")

        user = self.params.get("username") or self.params.get("user")
        password = self.params.get("password")
        host = self.params.get("host") or "127.0.0.1"
        port = int(self.params.get("port") or 1521)
        database = (
            self.params.get("service_name")
            or self.params.get("database")
            or self.params.get("database_name")
            or self.params.get("sid")
            or "FREEPDB1"
        )
        dsn = f"{host}:{port}/{database}"
        self.conn = oracledb.connect(user=user, password=password, dsn=dsn)
        self.cursor = self.conn.cursor()

    def _ensure_table_exists(
        self,
        table_name: str,
        target_schema: str,
        cols: Sequence[str],
        sample_row: Dict[str, Any],
        pk_columns: Optional[Sequence[str]] = None,
    ) -> None:
        self._connect()
        try:
            self.cursor.execute(
                "SELECT 1 FROM all_tables WHERE owner = :1 AND table_name = :2",
                (target_schema.upper(), table_name.upper()),
            )
            if self.cursor.fetchone():
                return
        except Exception:
            pass

        col_defs = []
        for c in cols:
            val = sample_row.get(c)
            if isinstance(val, int):
                col_type = "NUMBER(19)"
            elif isinstance(val, float):
                col_type = "NUMBER"
            elif isinstance(val, (bytes, bytearray)):
                col_type = "BLOB"
            else:
                col_type = "VARCHAR2(4000)"
            col_defs.append(f'"{c.upper()}" {col_type}')

        pk_clause = ""
        if pk_columns:
            pk_str = ", ".join(f'"{p.upper()}"' for p in pk_columns)
            pk_clause = f', PRIMARY KEY ({pk_str})'

        ddl = f'CREATE TABLE "{target_schema.upper()}"."{table_name.upper()}" ({", ".join(col_defs)}{pk_clause})'
        try:
            self.cursor.execute(ddl)
            self.conn.commit()
        except Exception as exc:
            logger.debug(f"[OracleTargetWriter] Auto create table notice: {exc}")

    def write_batch(
        self,
        table_name: str,
        batch: TransportBatch,
        target_schema: str = "DEVKROS_P8_M2_TGT",
        pk_columns: Optional[Sequence[str]] = None,
        allow_merge: bool = True,
    ) -> int:
        self.verify_fencing()
        if not batch.rows:
            return 0
        self._connect()

        cols = [c.upper() for c in batch.column_names]
        schema_up = target_schema.upper()
        tbl_up = table_name.upper()

        if batch.rows:
            self._ensure_table_exists(tbl_up, schema_up, cols, batch.rows[0], pk_columns)

        placeholders = [f":{i+1}" for i in range(len(cols))]
        quoted_cols = [f'"{c}"' for c in cols]
        sql = f'INSERT INTO "{schema_up}"."{tbl_up}" ({", ".join(quoted_cols)}) VALUES ({", ".join(placeholders)})'

        # Map row values maintaining case-insensitive column match and ISO timestamp conversion
        data_tuples = []
        from datetime import datetime
        for r in batch.rows:
            row_tuple = []
            for c in batch.column_names:
                v = r.get(c, r.get(c.lower(), r.get(c.upper())))
                if isinstance(v, str) and len(v) >= 10 and (v[4:5] == "-" and v[7:8] == "-"):
                    try:
                        clean_v = v.replace("Z", "+00:00")
                        v = datetime.fromisoformat(clean_v)
                    except Exception:
                        pass
                row_tuple.append(v)
            data_tuples.append(tuple(row_tuple))

        self._in_transaction = True
        try:
            self.cursor.executemany(sql, data_tuples)
            written = len(data_tuples)
            self._active_tx_uncommitted_rows += written
            return written
        except Exception as exc:
            # Fallback to row-by-row on unique constraint violation with MERGE/UPDATE or single insert
            if "ORA-00001" in str(exc) or "unique constraint" in str(exc).lower():
                written = 0
                for row_tup in data_tuples:
                    try:
                        self.cursor.execute(sql, row_tup)
                        written += 1
                    except Exception as single_err:
                        if ("ORA-00001" in str(single_err) or "unique constraint" in str(single_err).lower()) and allow_merge:
                            try:
                                pk_cols_up = [p.upper() for p in pk_columns if p.upper() in cols] if pk_columns else []
                                if not pk_cols_up or len(pk_cols_up) < 2:
                                    try:
                                        self.cursor.execute(f"""
                                            SELECT cc.column_name 
                                            FROM user_constraints c 
                                            JOIN user_cons_columns cc ON c.constraint_name = cc.constraint_name 
                                            WHERE c.table_name = '{tbl_up}' AND c.constraint_type = 'P' 
                                            ORDER BY cc.position
                                        """)
                                        rows_pk = self.cursor.fetchall()
                                        if rows_pk:
                                            pk_cols_up = [r[0].upper() for r in rows_pk if r[0].upper() in cols]
                                    except Exception:
                                        pass
                                if not pk_cols_up:
                                    pk_cols_up = [c for c in cols if c.endswith("_ID") or c == "ID"]
                                if not pk_cols_up and cols:
                                    pk_cols_up = [cols[0]]
                                non_pk_cols = [c for c in cols if c not in pk_cols_up]
                                if non_pk_cols:
                                    set_clause = ", ".join([f'"{c}" = :{i+1}' for i, c in enumerate(non_pk_cols)])
                                    pk_where = " AND ".join([f'"{p}" = :{len(non_pk_cols)+1+i}' for i, p in enumerate(pk_cols_up)])
                                    upd_sql = f'UPDATE "{schema_up}"."{tbl_up}" SET {set_clause} WHERE {pk_where}'
                                    row_map = dict(zip(cols, row_tup))
                                    upd_vals = tuple([row_map.get(c) for c in non_pk_cols] + [row_map.get(p) for p in pk_cols_up])
                                    self.cursor.execute(upd_sql, upd_vals)
                                written += 1
                            except Exception as upd_err:
                                logger.warning(f"[OracleTargetWriter] Update fallback error on {schema_up}.{tbl_up}: {upd_err}")
                        elif "ORA-00001" not in str(single_err):
                            raise single_err
                self._active_tx_uncommitted_rows += written
                return written
            raise exc

    def delete_batch(
        self,
        table_name: str,
        target_schema: str,
        pk_columns: Sequence[str],
        key_records: Sequence[Mapping[str, Any]],
    ) -> int:
        self.verify_fencing()
        if not key_records or not pk_columns:
            return 0
        self._connect()

        schema_up = target_schema.upper()
        tbl_up = table_name.upper()
        pks_up = [p.upper() for p in pk_columns]

        where_clauses = [f'"{pk}" = :{i+1}' for i, pk in enumerate(pks_up)]
        sql = f'DELETE FROM "{schema_up}"."{tbl_up}" WHERE {" AND ".join(where_clauses)}'

        data_tuples = []
        for rec in key_records:
            t = tuple(rec.get(pk, rec.get(pk.upper(), rec.get(pk.lower()))) for pk in pk_columns)
            data_tuples.append(t)

        self._in_transaction = True
        try:
            self.cursor.executemany(sql, data_tuples)
            deleted = self.cursor.rowcount if (hasattr(self.cursor, "rowcount") and self.cursor.rowcount >= 0) else len(key_records)
            self._active_tx_uncommitted_rows += deleted
            return deleted
        except Exception as exc:
            logger.warning(f"[OracleTargetWriter] Error executing delete_batch on {schema_up}.{tbl_up}: {exc}")
            raise exc

    def verify_uncertain_commit(
        self,
        table_name: str,
        target_schema: str,
        pk_columns: Sequence[str],
        batch: TransportBatch,
    ) -> CommitOutcomeState:
        if not batch.rows or not pk_columns:
            return CommitOutcomeState.UNKNOWN_COMMIT_OUTCOME
        self._connect()
        try:
            first_row = batch.rows[0]
            schema_up = target_schema.upper()
            tbl_up = table_name.upper()
            where_clauses = [f'"{pk.upper()}" = :{i+1}' for i, pk in enumerate(pk_columns)]
            sql = f'SELECT 1 FROM "{schema_up}"."{tbl_up}" WHERE {" AND ".join(where_clauses)}'
            bind_vals = tuple(first_row.get(pk, first_row.get(pk.lower(), first_row.get(pk.upper()))) for pk in pk_columns)
            self.cursor.execute(sql, bind_vals)
            if self.cursor.fetchone():
                return CommitOutcomeState.COMMITTED
            return CommitOutcomeState.NOT_COMMITTED
        except Exception:
            return CommitOutcomeState.UNKNOWN_COMMIT_OUTCOME

    def execute_ddl(self, ddl: str) -> None:
        if not ddl or not ddl.strip():
            return
        self._connect()
        try:
            self.cursor.execute(ddl)
            self.conn.commit()
        except Exception as exc:
            # Table or sequence already exists error handling (e.g. ORA-00955)
            if "ORA-00955" not in str(exc):
                logger.warning(f"[OracleTargetWriter] DDL Execution notice: {exc}")

    def commit(self) -> None:
        if self.conn:
            self.conn.commit()
        self._in_transaction = False
        self._active_tx_uncommitted_rows = 0

    def rollback(self) -> None:
        if self.conn:
            self.conn.rollback()
        self._in_transaction = False
        self._active_tx_uncommitted_rows = 0

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

