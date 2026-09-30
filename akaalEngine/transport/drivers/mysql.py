"""
akaalEngine.transport.drivers.mysql
====================================
Canonical High-Performance MySQL & MariaDB SourceReader and TargetWriter driver.
"""

import logging
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

try:
    import pymysql
    import pymysql.cursors
    _HAS_MYSQL = True
except ImportError:
    pymysql = None
    _HAS_MYSQL = False

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
from akaalEngine.transport.models.spec import PartitionStrategy, TransportPartition

logger = logging.getLogger("akaalEngine.transport.drivers.mysql")


class MySQLSourceReader(SourceReader):
    """
    High-performance MySQL fast-path reader using PyMySQL with cursor streaming
    and primary-key / range query chunking.
    """

    def __init__(self, connection_params: Dict[str, Any]):
        self.params = connection_params
        self.conn = None
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

    def _connect(self) -> None:
        if not _HAS_MYSQL:
            from akaalEngine.transport.models.errors import TransportCapabilityError
            raise TransportCapabilityError("pymysql library is not installed for MySQLSourceReader driver.")

        user = self.params.get("username") or self.params.get("user") or "root"
        password = self.params.get("password") or self.params.get("secret_ref") or ""
        host = self.params.get("host") or "localhost"
        port = int(self.params.get("port") or 3306)
        database = (
            self.params.get("database")
            or self.params.get("database_name")
            or self.params.get("dbname")
            or self.params.get("schema")
            or ""
        )
        if database in ("public", "main"):
            database = ""

        self.conn = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database or None,
            autocommit=True,
            charset="utf8mb4",
        )
        self.cursor = self.conn.cursor()

    def open_partition(self, partition: TransportPartition, last_committed_key: Optional[Any] = None) -> None:
        self.partition = partition
        self.sequence_number = 0
        self._last_key = last_committed_key

        if not self.conn or (hasattr(self.conn, "open") and not self.conn.open):
            self._connect()
        else:
            try:
                self.cursor = self.conn.cursor()
            except Exception:
                self._connect()

        if self.cursor:
            t_name = partition.table_name.strip()
            sch = partition.schema_name or ""
            if sch in ("public", "main", ""):
                table_ref = f"`{t_name}`"
            else:
                table_ref = f"`{sch}`.`{t_name}`"

            # Dynamically resolve primary key column from MySQL table metadata
            pk_col = None
            if partition.pk_columns and partition.pk_columns[0] != "id":
                pk_col = partition.pk_columns[0]

            if not pk_col:
                try:
                    self.cursor.execute(f"SHOW KEYS FROM {table_ref} WHERE Key_name = 'PRIMARY'")
                    pk_row = self.cursor.fetchone()
                    if pk_row and len(pk_row) > 4:
                        pk_col = pk_row[4]  # Column_name is index 4 in SHOW KEYS
                except Exception:
                    pass

            if not pk_col and partition.pk_columns:
                pk_col = partition.pk_columns[0]

            if not pk_col:
                try:
                    self.cursor.execute(f"SHOW COLUMNS FROM {table_ref}")
                    cols = [c[0] for c in self.cursor.fetchall()]
                    if cols:
                        pk_col = cols[0]
                except Exception:
                    pass

            if not pk_col:
                pk_col = "id"

            self._pk_col = pk_col
            pk_quoted = f"`{pk_col}`"

            sql = f"SELECT * FROM {table_ref}"
            conditions: List[str] = []
            exec_params: List[Any] = []

            if partition.lower_bound is not None and partition.upper_bound is not None:
                conditions.append(f"{pk_quoted} >= %s AND {pk_quoted} < %s")
                exec_params.extend([partition.lower_bound, partition.upper_bound])
            elif partition.is_null_partition:
                conditions.append(f"{pk_quoted} IS NULL")

            if last_committed_key is not None:
                conditions.append(f"{pk_quoted} > %s")
                exec_params.append(last_committed_key)

            if conditions:
                sql += " WHERE " + " AND ".join(conditions)
            sql += f" ORDER BY {pk_quoted} ASC"

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
            batch_id=f"mysql-batch-{self.sequence_number}",
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
            self.cursor = None
        if self.conn:
            try:
                self.conn.close()
            except Exception:
                pass
            self.conn = None


class MySQLTargetWriter(TargetWriter):
    """
    High-performance MySQL fast-path writer using PyMySQL batch insert
    with ON DUPLICATE KEY UPDATE / single-row fallback.
    """

    def __init__(self, connection_params: Dict[str, Any]):
        super().__init__(
            migration_id=connection_params.get("migration_id"),
            batch_id=connection_params.get("batch_id") or connection_params.get("job_id"),
            endpoint_identity=connection_params.get("endpoint_identity") or connection_params.get("host"),
        )
        self.params = connection_params
        self.conn = None
        self.cursor = None
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

    def _connect(self) -> None:
        if not _HAS_MYSQL:
            from akaalEngine.transport.models.errors import TransportCapabilityError
            raise TransportCapabilityError("pymysql library is not installed for MySQLTargetWriter driver.")

        user = self.params.get("username") or self.params.get("user") or "root"
        password = self.params.get("password") or self.params.get("secret_ref") or ""
        host = self.params.get("host") or "localhost"
        port = int(self.params.get("port") or 3306)
        database = (
            self.params.get("database")
            or self.params.get("database_name")
            or self.params.get("dbname")
            or self.params.get("schema")
            or ""
        )
        if database in ("public", "main"):
            database = ""

        self.conn = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database or None,
            autocommit=False,
            charset="utf8mb4",
        )
        self.cursor = self.conn.cursor()

    def _ensure_table_exists(
        self,
        table_name: str,
        target_schema: str,
        cols: Sequence[str],
        sample_row: Dict[str, Any],
        pk_columns: Optional[Sequence[str]] = None,
    ) -> None:
        if not self.conn:
            self._connect()
        try:
            sch = target_schema if target_schema not in ("public", "main", "") else self.params.get("database", "")
            if sch:
                self.cursor.execute(
                    "SELECT 1 FROM information_schema.tables WHERE table_schema = %s AND table_name = %s",
                    (sch, table_name),
                )
            else:
                self.cursor.execute(
                    "SELECT 1 FROM information_schema.tables WHERE table_name = %s",
                    (table_name,),
                )
            if self.cursor.fetchone():
                return
        except Exception:
            pass

        col_defs = []
        for c in cols:
            val = sample_row.get(c)
            if isinstance(val, int):
                col_type = "BIGINT"
            elif isinstance(val, float):
                col_type = "DOUBLE"
            elif isinstance(val, (bytes, bytearray)):
                col_type = "BLOB"
            else:
                col_type = "VARCHAR(255)"
            col_defs.append(f"`{c}` {col_type}")

        pk_clause = ""
        if pk_columns:
            pk_str = ", ".join(f"`{p}`" for p in pk_columns)
            pk_clause = f", PRIMARY KEY ({pk_str})"

        t_ref = f"`{table_name}`"
        if target_schema not in ("public", "main", ""):
            t_ref = f"`{target_schema}`.`{table_name}`"

        ddl = f"CREATE TABLE IF NOT EXISTS {t_ref} ({', '.join(col_defs)}{pk_clause}) ENGINE=InnoDB"
        try:
            self.cursor.execute(ddl)
            self.conn.commit()
        except Exception as exc:
            logger.debug(f"[MySQLTargetWriter] Auto-create table notice: {exc}")

    def write_batch(
        self,
        table_name: str,
        batch: TransportBatch,
        target_schema: str = "public",
        pk_columns: Optional[Sequence[str]] = None,
        allow_merge: bool = True,
    ) -> int:
        self.verify_fencing()
        if not batch.rows:
            return 0
        if not self.conn:
            self._connect()

        cols = list(batch.column_names)
        if batch.rows:
            self._ensure_table_exists(table_name, target_schema, cols, batch.rows[0], pk_columns)

        t_ref = f"`{table_name}`"
        if target_schema not in ("public", "main", ""):
            t_ref = f"`{target_schema}`.`{table_name}`"

        col_list = ", ".join(f"`{c}`" for c in cols)
        val_placeholders = ", ".join("%s" for _ in cols)

        dup_clause = ""
        if allow_merge:
            pk_set = set(pk_columns) if pk_columns else set()
            non_pk_cols = [c for c in cols if c not in pk_set]
            if non_pk_cols:
                set_items = [f"`{c}`=VALUES(`{c}`)" for c in non_pk_cols]
                dup_clause = f" ON DUPLICATE KEY UPDATE {', '.join(set_items)}"

        sql = f"INSERT INTO {t_ref} ({col_list}) VALUES ({val_placeholders}){dup_clause}"


        import json
        data_tuples = []
        for r in batch.rows:
            row_vals = []
            for c in cols:
                v = r.get(c) if c in r else (r.get(c.lower()) if c.lower() in r else r.get(c.upper()))
                if isinstance(v, (dict, list)):
                    v = json.dumps(v)
                elif isinstance(v, memoryview):
                    v = bytes(v)
                elif hasattr(v, "hex") and not isinstance(v, (str, bytes, bytearray)):
                    v = str(v)
                row_vals.append(v)
            data_tuples.append(tuple(row_vals))


        self._in_transaction = True
        try:
            self.cursor.executemany(sql, data_tuples)
            written = len(data_tuples)
            self._active_tx_uncommitted_rows += written
            return written
        except Exception as exc:
            if "1062" in str(exc) or "Duplicate entry" in str(exc):
                # Fallback to row-by-row
                written = 0
                for row_tup in data_tuples:
                    try:
                        self.cursor.execute(sql, row_tup)
                        written += 1
                    except Exception as s_err:
                        if "1062" not in str(s_err) and "Duplicate entry" not in str(s_err):
                            raise s_err
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
        if not self.conn:
            self._connect()

        t_ref = f"`{table_name}`"
        if target_schema not in ("public", "main", ""):
            t_ref = f"`{target_schema}`.`{table_name}`"

        where_clauses = [f"`{pk}` = %s" for pk in pk_columns]
        sql = f"DELETE FROM {t_ref} WHERE {' AND '.join(where_clauses)}"

        data_tuples = []
        for rec in key_records:
            t = tuple(rec.get(pk, rec.get(pk.lower(), rec.get(pk.upper()))) for pk in pk_columns)
            data_tuples.append(t)

        self._in_transaction = True
        try:
            self.cursor.executemany(sql, data_tuples)
            deleted = self.cursor.rowcount if (hasattr(self.cursor, "rowcount") and self.cursor.rowcount >= 0) else len(key_records)
            self._active_tx_uncommitted_rows += deleted
            return deleted
        except Exception as exc:
            logger.warning(f"[MySQLTargetWriter] Error executing delete_batch on {t_ref}: {exc}")
            raise exc

    def commit(self) -> None:
        self.commit_transaction()

    def rollback(self) -> None:
        self.rollback_transaction()

    def cancel(self) -> None:
        if self.conn and _HAS_MYSQL:
            try:
                self.conn.close()
            except Exception:
                pass

    def verify_uncertain_commit(
        self,
        table_name: str,
        target_schema: str,
        pk_columns: Sequence[str],
        batch: TransportBatch,
    ) -> CommitOutcomeState:
        if not batch.rows or not pk_columns:
            return CommitOutcomeState.COMMITTED
        self._connect()
        try:
            t_ref = f"`{table_name}`"
            if target_schema not in ("public", "main", ""):
                t_ref = f"`{target_schema}`.`{table_name}`"
            sample = batch.rows[0]
            pk = pk_columns[0]
            val = sample.get(pk, sample.get(pk.lower(), sample.get(pk.upper())))
            sql = f"SELECT COUNT(*) FROM {t_ref} WHERE `{pk}` = %s"
            self.cursor.execute(sql, (val,))
            cnt = self.cursor.fetchone()[0]
            if cnt > 0:
                return CommitOutcomeState.COMMITTED
            return CommitOutcomeState.NOT_COMMITTED
        except Exception:
            return CommitOutcomeState.UNKNOWN_COMMIT_OUTCOME

    def execute_ddl(self, ddl_statements: Sequence[str]) -> int:
        self.verify_fencing()
        if not ddl_statements:
            return 0
        self._connect()
        applied = 0
        for ddl in ddl_statements:
            cleaned = ddl.strip()
            if not cleaned:
                continue
            try:
                self.cursor.execute(cleaned)
                self.conn.commit()
                applied += 1
            except Exception as exc:
                logger.warning(f"[MySQLTargetWriter] DDL execution notice: {exc}")
        return applied

    def commit_transaction(self) -> CommitOutcomeState:
        self.verify_fencing()
        if not self._in_transaction or not self.conn:
            return CommitOutcomeState.COMMITTED
        try:
            self.conn.commit()
            self._in_transaction = False
            self._active_tx_uncommitted_rows = 0
            return CommitOutcomeState.COMMITTED
        except Exception as exc:
            logger.warning(f"[MySQLTargetWriter] Commit failed: {exc}")
            self._in_transaction = False
            return CommitOutcomeState.UNCERTAIN

    def rollback_transaction(self) -> None:
        if self._in_transaction and self.conn:
            try:
                self.conn.rollback()
            except Exception:
                pass
            finally:
                self._in_transaction = False
                self._active_tx_uncommitted_rows = 0

    def close(self) -> None:
        self.rollback_transaction()
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

