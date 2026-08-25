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

        if not self.conn:
            self._connect()

        cols = batch.column_names
        col_str = ", ".join([f'"{c}"' for c in cols])

        on_conflict_clause = ""
        if allow_merge and pk_columns:
            pk_str = ", ".join([f'"{p}"' for p in pk_columns])
            on_conflict_clause = f" ON CONFLICT ({pk_str}) DO NOTHING"

        sql = f'INSERT INTO "{target_schema}"."{table_name}" ({col_str}) VALUES %s{on_conflict_clause}'
        data_tuples = [tuple(r.get(c) for c in cols) for r in batch.rows]

        self._in_transaction = True
        try:
            psycopg2.extras.execute_values(self.cursor, sql, data_tuples)
            written = self.cursor.rowcount if (hasattr(self.cursor, "rowcount") and self.cursor.rowcount >= 0) else len(batch.rows)
            self._active_tx_uncommitted_rows += written
            return written
        except Exception as exc:
            logger.warning(f"[PostgreSQLTargetWriter] Vectorized execute_values failed: {exc}. Retrying row-by-row...")
            try:
                self.conn.rollback()
            except Exception:
                pass
            self._active_tx_uncommitted_rows = 0
            written = 0
            single_sql = f'INSERT INTO "{target_schema}"."{table_name}" ({col_str}) VALUES ({", ".join(["%s"] * len(cols))}){on_conflict_clause}'
            for tup in data_tuples:
                try:
                    self.cursor.execute("SAVEPOINT sp_row;")
                    self.cursor.execute(single_sql, tup)
                    inserted = self.cursor.rowcount if (hasattr(self.cursor, "rowcount") and self.cursor.rowcount >= 0) else 0
                    self.cursor.execute("RELEASE SAVEPOINT sp_row;")
                    written += inserted
                except Exception:
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

    def verify_uncertain_commit(
        self,
        table_name: str,
        target_schema: str,
        pk_columns: Sequence[str],
        batch: TransportBatch,
    ) -> CommitOutcomeState:
        """
        Verifies whether an un-acknowledged batch fully committed, failed, or is ambiguous.
        FAIL CLOSED -> UNKNOWN_COMMIT_OUTCOME unless authoritative proof exists.
        """
        return CommitOutcomeState.UNKNOWN_COMMIT_OUTCOME

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
        if self.conn:
            try:
                self.conn.close()
            except Exception:
                pass
