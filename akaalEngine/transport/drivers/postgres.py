"""
akaalEngine.transport.drivers.postgres
=======================================
Canonical High-Performance PostgreSQL TargetWriter driver mined from `akaal/engine/writer.py`.
"""

import logging
from typing import Any, Dict, List, Optional, Sequence, Tuple

try:
    import psycopg2
    import psycopg2.extras
    _HAS_PG = True
except ImportError:
    psycopg2 = None
    _HAS_PG = False

from akaalEngine.transport.drivers.base import TargetWriter
from akaalEngine.transport.models.batch import TransportBatch
from akaalEngine.transport.models.capabilities import (
    CancellationCapability,
    CommitOutcomeState,
    IdempotencyMode,
    LOBMode,
    ProviderCapabilities,
    ResumabilityMode,
)

logger = logging.getLogger("akaalEngine.transport.drivers.postgres")


class PostgreSQLTargetWriter(TargetWriter):
    """
    High-performance PostgreSQL fast-path writer using psycopg2.extras.execute_values
    vectorized array binding with single-row isolation fallback on conflict.
    Mined from `akaal/engine/writer.py`.
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
        if not _HAS_PG:
            from akaalEngine.transport.models.errors import TransportCapabilityError
            raise TransportCapabilityError("psycopg2 library is not installed for PostgreSQLTargetWriter driver.")

        pg_keys = {"host", "port", "user", "password", "dbname", "sslmode", "connect_timeout", "options"}
        raw_params = dict(self.params)

        user_val = raw_params.pop("user", None) or raw_params.pop("username", None)
        dbname_val = raw_params.pop("dbname", None) or raw_params.pop("database", None) or raw_params.pop("database_name", None)

        pg_params = {}
        if user_val:
            pg_params["user"] = user_val
        if dbname_val:
            pg_params["dbname"] = dbname_val

        for k, v in raw_params.items():
            if k in pg_keys and v is not None:
                pg_params[k] = v

        self.conn = psycopg2.connect(**pg_params)
        self.cursor = self.conn.cursor()

    def _ensure_table_exists(
        self,
        table_name: str,
        target_schema: str,
        cols: Sequence[str],
        sample_row: Dict[str, Any],
        pk_columns: Optional[Sequence[str]] = None,
    ) -> None:
        if not self.conn or (hasattr(self.conn, "closed") and self.conn.closed):
            self._connect()
        elif not self.cursor or (hasattr(self.cursor, "closed") and self.cursor.closed):
            try:
                self.cursor = self.conn.cursor()
            except Exception:
                self._connect()
        try:
            self.cursor.execute(
                "SELECT 1 FROM information_schema.tables WHERE table_schema = %s AND table_name = %s",
                (target_schema, table_name.lower()),
            )
            if self.cursor.fetchone():
                return
            self.cursor.execute(
                "SELECT 1 FROM information_schema.tables WHERE table_schema = %s AND table_name = %s",
                (target_schema, table_name),
            )
            if self.cursor.fetchone():
                return

            col_defs = []
            for col in cols:
                val = sample_row.get(col)
                if isinstance(val, bool):
                    col_type = "BOOLEAN"
                elif isinstance(val, int):
                    col_type = "BIGINT"
                elif isinstance(val, float):
                    col_type = "NUMERIC"
                elif hasattr(val, "isoformat") or (hasattr(val, "year") and hasattr(val, "month")):
                    col_type = "TIMESTAMP"
                elif isinstance(val, bytes):
                    col_type = "BYTEA"
                else:
                    col_type = "TEXT"
                col_defs.append(f'"{col}" {col_type}')

            if pk_columns:
                pk_str = ", ".join([f'"{p}"' for p in pk_columns])
                col_defs.append(f"PRIMARY KEY ({pk_str})")

            create_sql = f'CREATE TABLE IF NOT EXISTS "{target_schema}"."{table_name}" (\n  ' + ",\n  ".join(col_defs) + "\n)"
            self.cursor.execute(create_sql)
            self.conn.commit()
        except Exception as exc:
            logger.warning(f"[PostgreSQLTargetWriter] _ensure_table_exists for {target_schema}.{table_name}: {exc}")
            try:
                self.conn.rollback()
            except Exception:
                pass

    def write_batch(
        self,
        table_name: str,
        batch: TransportBatch,
        target_schema: str = "public",
        pk_columns: Optional[Sequence[str]] = None,
        allow_merge: bool = True,
    ) -> int:
        if not batch.rows:
            return 0

        if not self.conn or (hasattr(self.conn, "closed") and self.conn.closed):
            self._connect()
        elif not self.cursor or (hasattr(self.cursor, "closed") and self.cursor.closed):
            try:
                self.cursor = self.conn.cursor()
            except Exception:
                self._connect()

        cols = batch.column_names
        from akaalEngine.schema.ddl.identifiers import IdentifierSanitizer
        t_clean = IdentifierSanitizer.sanitize_identifier(table_name, "POSTGRESQL")
        s_clean = IdentifierSanitizer.sanitize_identifier(target_schema, "POSTGRESQL")
        cols_clean = [IdentifierSanitizer.sanitize_identifier(c, "POSTGRESQL") for c in cols]
        col_str = ", ".join([f'"{c}"' for c in cols_clean])

        self._ensure_table_exists(t_clean, s_clean, cols_clean, batch.rows[0] if batch.rows else {}, pk_columns)

        on_conflict_clause = ""
        if allow_merge:
            pk_resolved = list(pk_columns) if pk_columns else []
            if not pk_resolved:
                try:
                    self.cursor.execute("""
                        SELECT kcu.column_name
                        FROM information_schema.table_constraints tc
                        JOIN information_schema.key_column_usage kcu
                          ON tc.constraint_name = kcu.constraint_name AND tc.table_schema = kcu.table_schema
                        WHERE tc.constraint_type = 'PRIMARY KEY' AND tc.table_name = %s AND tc.table_schema = %s
                        ORDER BY kcu.ordinal_position
                    """, (t_clean, s_clean))
                    rows_pk = self.cursor.fetchall()
                    if rows_pk:
                        pk_resolved = [r[0] for r in rows_pk if r[0] in cols]
                except Exception:
                    pass
            if pk_resolved:
                pk_clean = [IdentifierSanitizer.sanitize_identifier(p, "POSTGRESQL") for p in pk_resolved]
                pk_str = ", ".join([f'"{p}"' for p in pk_clean])
                non_pk_clean = [IdentifierSanitizer.sanitize_identifier(c, "POSTGRESQL") for c in cols if c not in pk_resolved]
                if non_pk_clean:
                    set_clause = ", ".join([f'"{c}" = EXCLUDED."{c}"' for c in non_pk_clean])
                    on_conflict_clause = f" ON CONFLICT ({pk_str}) DO UPDATE SET {set_clause}"
                else:
                    on_conflict_clause = f" ON CONFLICT ({pk_str}) DO NOTHING"

        sql = f'INSERT INTO "{s_clean}"."{t_clean}" ({col_str}) VALUES %s{on_conflict_clause}'
        data_tuples = [tuple(r.get(c) if c in r else r.get(c.upper(), r.get(c.lower())) for c in cols) for r in batch.rows]

        self._in_transaction = True
        try:
            psycopg2.extras.execute_values(self.cursor, sql, data_tuples)
            written = self.cursor.rowcount if (hasattr(self.cursor, "rowcount") and self.cursor.rowcount >= 0) else len(batch.rows)
            self._active_tx_uncommitted_rows += written
            return written
        except Exception as exc:
            logger.warning(f"[PostgreSQLTargetWriter] Vectorized execute_values failed: {exc}. Retrying row-by-row...")
            import traceback
            logger.debug(f"[PostgreSQLTargetWriter] Vectorized traceback:\n{traceback.format_exc()}")
            try:
                self.conn.rollback()
            except Exception:
                pass
            self._active_tx_uncommitted_rows = 0
            written = 0
            single_sql = f'INSERT INTO "{s_clean}"."{t_clean}" ({col_str}) VALUES ({", ".join(["%s"] * len(cols))}){on_conflict_clause}'
            for tup in data_tuples:
                try:
                    self.cursor.execute("SAVEPOINT sp_row;")
                    self.cursor.execute(single_sql, tup)
                    inserted = self.cursor.rowcount if (hasattr(self.cursor, "rowcount") and self.cursor.rowcount >= 0) else 0
                    self.cursor.execute("RELEASE SAVEPOINT sp_row;")
                    written += inserted
                except Exception as row_exc:
                    logger.warning(f"[PostgreSQLTargetWriter] Single row insert failed: {row_exc} | Row: {tup}")
                    try:
                        self.cursor.execute("ROLLBACK TO SAVEPOINT sp_row;")
                    except Exception:
                        self.conn.rollback()
                        self._in_transaction = False
                        self._active_tx_uncommitted_rows = 0
                        written = 0
                        raise
            if written > 0:
                self._active_tx_uncommitted_rows += written
            return written

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

        from akaalEngine.schema.ddl.identifiers import IdentifierSanitizer
        t_clean = IdentifierSanitizer.sanitize_identifier(table_name, "POSTGRESQL")
        s_clean = IdentifierSanitizer.sanitize_identifier(target_schema, "POSTGRESQL")
        pk_clean = [IdentifierSanitizer.sanitize_identifier(pk, "POSTGRESQL") for pk in pk_columns]

        where_clause = " AND ".join([f'"{pk}" = %s' for pk in pk_clean])
        sql = f'DELETE FROM "{s_clean}"."{t_clean}" WHERE {where_clause}'

        data_tuples = [
            tuple(rec.get(pk) if pk in rec else (rec.get(pk.upper(), rec.get(pk.lower()))) for pk in pk_columns)
            for rec in key_records
        ]

        self._in_transaction = True
        try:
            self.cursor.executemany(sql, data_tuples)
            deleted_count = self.cursor.rowcount if (hasattr(self.cursor, "rowcount") and self.cursor.rowcount >= 0) else len(key_records)
            self._active_tx_uncommitted_rows += deleted_count
            return deleted_count
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
        """
        Physical PK/row requery to determine exact commit outcome after failure or timeout.
        """
        if not batch or not batch.rows:
            return CommitOutcomeState.COMMITTED
        if not self.conn:
            try:
                self._connect()
            except Exception:
                return CommitOutcomeState.UNKNOWN_COMMIT_OUTCOME
        try:
            from akaalEngine.schema.ddl.identifiers import IdentifierSanitizer
            t_clean = IdentifierSanitizer.sanitize_identifier(table_name, "POSTGRESQL")
            s_clean = IdentifierSanitizer.sanitize_identifier(target_schema, "POSTGRESQL")
            pk_col = pk_columns[0] if pk_columns else (batch.column_names[0] if batch.column_names else None)
            if not pk_col:
                return CommitOutcomeState.UNKNOWN_COMMIT_OUTCOME
            pk_clean = IdentifierSanitizer.sanitize_identifier(pk_col, "POSTGRESQL")
            pk_vals = [r.get(pk_col) if pk_col in r else r.get(pk_col.upper(), r.get(pk_col.lower())) for r in batch.rows if (r.get(pk_col) is not None or r.get(pk_col.upper()) is not None or r.get(pk_col.lower()) is not None)]
            if not pk_vals:
                return CommitOutcomeState.UNKNOWN_COMMIT_OUTCOME
            with self.conn.cursor() as cur:
                cur.execute(
                    f'SELECT COUNT(*) FROM "{s_clean}"."{t_clean}" WHERE "{pk_clean}" = ANY(%s)',
                    (pk_vals,)
                )
                found = cur.fetchone()[0]
                if found == len(batch.rows):
                    return CommitOutcomeState.COMMITTED
                elif found == 0:
                    return CommitOutcomeState.NOT_COMMITTED
                else:
                    return CommitOutcomeState.UNKNOWN_COMMIT_OUTCOME
        except Exception as exc:
            logger.warning(f"[PostgreSQLTargetWriter] verify_uncertain_commit check failed: {exc}")
            return CommitOutcomeState.UNKNOWN_COMMIT_OUTCOME

    def execute_ddl(self, ddl: str) -> None:
        """Executes a DDL statement on PostgreSQL target database."""
        if not ddl or not ddl.strip():
            return
        if not self.conn:
            self._connect()
        try:
            self.cursor.execute(ddl)
            self.conn.commit()
        except Exception as exc:
            logger.warning(f"[PostgreSQLTargetWriter] execute_ddl failed: {exc} | DDL: {ddl[:100]}...")
            try:
                self.conn.rollback()
            except Exception:
                pass
            raise

    def commit(self) -> None:
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
