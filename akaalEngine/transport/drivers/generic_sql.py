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


def _create_sql_connection(params: Dict[str, Any]) -> Any:
    """Dynamically establishes a physical database connection for any SQL provider."""
    if not params:
        return None
    if params.get("db_connection"):
        return params["db_connection"]
    if params.get("connection") or params.get("raw_connection"):
        return params.get("connection") or params.get("raw_connection")

    prov = str(params.get("provider_id") or params.get("provider") or params.get("engine") or "").lower()
    host = params.get("host") or params.get("server") or "localhost"
    port = params.get("port")
    user = params.get("username") or params.get("user") or params.get("db_user")
    password = params.get("password") or params.get("db_password") or ""
    database = (
        params.get("database")
        or params.get("database_name")
        or params.get("dbname")
        or params.get("db_name")
        or params.get("service_name")
        or ""
    )

    try:
        if prov in ("mysql", "mariadb", "tidb", "singlestore") or (not prov and int(port or 0) == 3306):
            import pymysql
            return pymysql.connect(
                host=host,
                port=int(port or 3306),
                user=user or "root",
                password=password,
                database=database,
                autocommit=True,
            )
        elif prov in ("postgres", "postgresql", "cockroachdb", "yugabytedb") or (not prov and int(port or 0) == 5432):
            import psycopg2
            return psycopg2.connect(
                host=host,
                port=int(port or 5432),
                user=user or "postgres",
                password=password,
                dbname=database or "postgres",
            )
        elif prov in ("oracle", "orcl") or (not prov and int(port or 0) == 1521):
            import oracledb
            dsn = f"{host}:{int(port or 1521)}/{database or 'FREEPDB1'}"
            return oracledb.connect(user=user, password=password, dsn=dsn)
        elif prov == "sqlite" or (database and (database.endswith(".db") or database.endswith(".sqlite") or database == ":memory:")):
            import sqlite3
            return sqlite3.connect(database or ":memory:")
        elif prov in ("mssql", "sqlserver") or (not prov and int(port or 0) == 1433):
            try:
                import pyodbc
                conn_str = f"DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={host},{int(port or 1433)};DATABASE={database};UID={user};PWD={password};TrustServerCertificate=yes;"
                return pyodbc.connect(conn_str)
            except Exception:
                import pymssql
                return pymssql.connect(server=host, port=int(port or 1433), user=user, password=password, database=database)
    except Exception as exc:
        logger.debug(f"[_create_sql_connection] Connection attempt for {prov} failed: {exc}")

    if database and (database.endswith(".db") or database.endswith(".sqlite")):
        import sqlite3
        return sqlite3.connect(database)

    return None


def _format_table_ref(schema: Optional[str], table: str, connection: Any) -> str:
    mod = type(connection).__module__.lower() if connection else ""
    if "mysql" in mod or "mariadb" in mod or "pymysql" in mod:
        if schema and schema not in ("public", "main", ""):
            return f"`{schema}`.`{table}`"
        return f"`{table}`"
    elif "mssql" in mod or "pyodbc" in mod or "pymssql" in mod:
        if schema and schema not in ("main", ""):
            return f"[{schema}].[{table}]"
        return f"[{table}]"
    else:
        if schema and schema not in ("main", "public", ""):
            return f'"{schema}"."{table}"'
        return f'"{table}"'


def _quote_identifier(name: str, connection: Any) -> str:
    mod = type(connection).__module__.lower() if connection else ""
    if "mysql" in mod or "mariadb" in mod or "pymysql" in mod:
        return f"`{name}`"
    elif "mssql" in mod or "pyodbc" in mod or "pymssql" in mod:
        return f"[{name}]"
    return f'"{name}"'


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

        if not self.conn or (hasattr(self.conn, "closed") and self.conn.closed) or (hasattr(self.conn, "open") and not self.conn.open):
            self.conn = _create_sql_connection(self.params)
            if self.conn:
                self.cursor = self.conn.cursor()
        else:
            try:
                self.cursor = self.conn.cursor()
            except Exception:
                self.conn = _create_sql_connection(self.params)
                if self.conn:
                    self.cursor = self.conn.cursor()

        if self.cursor:
            pk_col = partition.pk_columns[0] if partition.pk_columns else "id"
            self._pk_col = pk_col
            table_ref = _format_table_ref(partition.schema_name, partition.table_name, self.conn)
            pk_quoted = _quote_identifier(pk_col, self.conn)

            sql = f"SELECT * FROM {table_ref}"
            conditions: List[str] = []
            exec_params: List[Any] = []
            if partition.lower_bound is not None and partition.upper_bound is not None:
                conditions.append(f"{pk_quoted} >= {partition.lower_bound} AND {pk_quoted} < {partition.upper_bound}")
            elif partition.is_null_partition:
                conditions.append(f"{pk_quoted} IS NULL")
            if last_committed_key is not None:
                paramstyle = _resolve_paramstyle(self.conn)
                placeholder = _build_placeholder(paramstyle, 1)
                conditions.append(f"{pk_quoted} > {placeholder}")
                exec_params.append(last_committed_key)
            if conditions:
                sql += " WHERE " + " AND ".join(conditions)
            sql += f" ORDER BY {pk_quoted}"
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
            self.cursor = None
        if self.conn:
            try:
                self.conn.close()
            except Exception:
                pass
            self.conn = None


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

    def _connect(self) -> None:
        if self.conn is not None:
            if (hasattr(self.conn, "closed") and self.conn.closed) or (hasattr(self.conn, "open") and not self.conn.open):
                self.conn = None
                self.cursor = None
        if self.conn is not None and self.cursor is not None:
            return
        if self.params.get("db_connection"):
            self.conn = self.params["db_connection"]
            self.cursor = self.conn.cursor()
            return
        self.conn = _create_sql_connection(self.params)
        if self.conn:
            self.cursor = self.conn.cursor()
        else:
            from akaalEngine.transport.models.errors import TransportWriteError
            raise TransportWriteError("GenericSQLTargetWriter has no active database connection or cursor.")

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
        self._connect()

        cols = batch.column_names
        paramstyle = _resolve_paramstyle(self.conn)
        placeholders = _build_placeholder(paramstyle, len(cols))

        on_conflict_clause = ""
        if allow_merge and pk_columns:
            pk_cols = [str(p) for p in pk_columns]
            pk_cols_upper = set(p.upper() for p in pk_cols)
            non_pk_cols = [c for c in cols if str(c).upper() not in pk_cols_upper]
            driver_mod = type(self.conn).__module__.lower() if self.conn else ""
            if "sqlite" in driver_mod or "sqlite3" in driver_mod:
                pk_str = ", ".join([f'"{p}"' for p in pk_cols])
                if non_pk_cols:
                    set_str = ", ".join([f'"{c}" = excluded."{c}"' for c in non_pk_cols])
                    on_conflict_clause = f" ON CONFLICT ({pk_str}) DO UPDATE SET {set_str}"
                else:
                    on_conflict_clause = f" ON CONFLICT ({pk_str}) DO NOTHING"
            elif "mysql" in driver_mod or "mariadb" in driver_mod or "pymysql" in driver_mod:
                if non_pk_cols:
                    set_str = ", ".join([f'`{c}` = VALUES(`{c}`)' for c in non_pk_cols])
                    on_conflict_clause = f" ON DUPLICATE KEY UPDATE {set_str}"
                else:
                    on_conflict_clause = f" ON DUPLICATE KEY UPDATE `{pk_cols[0]}` = `{pk_cols[0]}`"

        table_ref = _format_table_ref(target_schema, table_name, self.conn)
        quoted_cols = ", ".join([_quote_identifier(c, self.conn) for c in cols])
        sql = f"INSERT INTO {table_ref} ({quoted_cols}) VALUES ({placeholders}){on_conflict_clause}"
        data_tuples = [tuple(r.get(c, r.get(c.lower(), r.get(c.upper()))) for c in cols) for r in batch.rows]
        try:
            self.cursor.executemany(sql, data_tuples)
            written = self.cursor.rowcount if (hasattr(self.cursor, "rowcount") and self.cursor.rowcount >= 0) else len(batch.rows)
            self._active_tx_uncommitted_rows += written
            return written
        except Exception as exc:
            if allow_merge and pk_columns:
                pk_cols = [str(p) for p in pk_columns]
                pk_cols_upper = set(p.upper() for p in pk_cols)
                non_pk_cols = [c for c in cols if str(c).upper() not in pk_cols_upper]
                if non_pk_cols:
                    written_count = 0
                    for r, tuple_val in zip(batch.rows, data_tuples):
                        set_clauses = [f"{_quote_identifier(c, self.conn)} = {_build_placeholder(paramstyle, 1)}" for c in non_pk_cols]
                        where_clauses = [f"{_quote_identifier(p, self.conn)} = {_build_placeholder(paramstyle, 1)}" for p in pk_cols]
                        update_sql = f"UPDATE {table_ref} SET {', '.join(set_clauses)} WHERE {' AND '.join(where_clauses)}"
                        update_params = [r.get(c, r.get(c.lower(), r.get(c.upper()))) for c in non_pk_cols] + [r.get(p, r.get(p.lower(), r.get(p.upper()))) for p in pk_cols]
                        try:
                            self.cursor.execute(update_sql, tuple(update_params))
                            rc = getattr(self.cursor, "rowcount", -1)
                            if rc > 0:
                                written_count += rc
                            elif rc == 0:
                                single_insert_sql = f"INSERT INTO {table_ref} ({quoted_cols}) VALUES ({placeholders})"
                                self.cursor.execute(single_insert_sql, tuple_val)
                                written_count += 1
                            else:
                                # rc == -1 (driver rowcount unmeasured/unavailable for execute); statement succeeded without exception
                                written_count += 1
                        except Exception as inner_exc:
                            logger.debug(f"[GenericSQLTargetWriter] Row upsert fallback error: {inner_exc}")
                            raise inner_exc
                    self._active_tx_uncommitted_rows += written_count
                    return written_count
            self._in_transaction = True
            raise

    def delete_batch(
        self,
        table_name: str,
        target_schema: str,
        pk_columns: Any,
        key_records: Any,
    ) -> int:
        self.verify_fencing()
        if not key_records or not pk_columns:
            return 0
        self._connect()

        paramstyle = _resolve_paramstyle(self.conn)
        where_clauses = []
        for i, pk in enumerate(pk_columns):
            pk_q = _quote_identifier(str(pk), self.conn)
            if paramstyle in ("format", "pyformat"):
                where_clauses.append(f"{pk_q} = %s")
            elif paramstyle == "numeric":
                where_clauses.append(f"{pk_q} = :{i+1}")
            elif paramstyle == "named":
                where_clauses.append(f"{pk_q} = :p{i}")
            else:
                where_clauses.append(f"{pk_q} = ?")

        table_ref = _format_table_ref(target_schema, table_name, self.conn)
        sql = f"DELETE FROM {table_ref} WHERE {' AND '.join(where_clauses)}"
        data_tuples = [
            tuple(rec.get(pk, rec.get(pk.upper(), rec.get(pk.lower()))) for pk in pk_columns)
            for rec in key_records
        ]
        self._in_transaction = True
        try:
            self.cursor.executemany(sql, data_tuples)
            deleted = self.cursor.rowcount if (hasattr(self.cursor, "rowcount") and self.cursor.rowcount >= 0) else len(key_records)
            self._active_tx_uncommitted_rows += deleted
            return deleted
        except Exception:
            self._in_transaction = True
            raise

    def execute_ddl(self, ddl: str) -> None:
        """Executes a DDL statement on the target database."""
        if not ddl or not ddl.strip():
            return
        self._connect()
        try:
            self.cursor.execute(ddl)
            if hasattr(self.conn, "commit"):
                self.conn.commit()
        except Exception as exc:
            logger.debug(f"[GenericSQLTargetWriter] DDL execution notice: {exc}")

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
            self.cursor = None
        if self.conn:
            try:
                self.conn.close()
            except Exception:
                pass
            self.conn = None

