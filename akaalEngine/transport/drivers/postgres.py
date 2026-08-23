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
        self.params = connection_params
        self.conn = None
        self.cursor = None

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
        if not _HAS_PG or self.params.get("mock_mode"):
            return
        user = self.params.get("username") or self.params.get("user") or "postgres"
        password = self.params.get("password")
        host = self.params.get("host") or "127.0.0.1"
        port = int(self.params.get("port") or 5432)
        dbname = self.params.get("database") or self.params.get("database_name") or "postgres"

        self.conn = psycopg2.connect(host=host, port=port, user=user, password=password, dbname=dbname)
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

        if not self.conn and _HAS_PG and not self.params.get("mock_mode"):
            self._connect()

        if self.params.get("mock_mode"):
            return len(batch.rows)

        cols = batch.column_names
        col_str = ", ".join([f'"{c}"' for c in cols])

        on_conflict_clause = ""
        if allow_merge and pk_columns:
            pk_str = ", ".join([f'"{p}"' for p in pk_columns])
            on_conflict_clause = f" ON CONFLICT ({pk_str}) DO NOTHING"

        sql = f'INSERT INTO "{target_schema}"."{table_name}" ({col_str}) VALUES %s{on_conflict_clause}'
        data_tuples = [tuple(r.get(c) for c in cols) for r in batch.rows]

        try:
            psycopg2.extras.execute_values(self.cursor, sql, data_tuples)
            return len(batch.rows)
        except Exception as exc:
            logger.warning(f"[PostgreSQLTargetWriter] Vectorized execute_values failed: {exc}. Retrying row-by-row...")
            self.conn.rollback()
            written = 0
            single_sql = f'INSERT INTO "{target_schema}"."{table_name}" ({col_str}) VALUES ({", ".join(["%s"] * len(cols))}){on_conflict_clause}'
            for tup in data_tuples:
                try:
                    self.cursor.execute(single_sql, tup)
                    written += 1
                except Exception:
                    self.conn.rollback()
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
        FAIL CLOSED -> UNKNOWN_COMMIT_OUTCOME unless primary key bounds prove 100% presence.
        """
        if not batch.rows or not pk_columns or not self.cursor:
            return CommitOutcomeState.UNKNOWN_COMMIT_OUTCOME

        pk_col = pk_columns[0]
        pk_vals = [r.get(pk_col) for r in batch.rows if r.get(pk_col) is not None]
        if not pk_vals:
            return CommitOutcomeState.UNKNOWN_COMMIT_OUTCOME

        try:
            sql = f'SELECT COUNT(*) FROM "{target_schema}"."{table_name}" WHERE "{pk_col}" IN %s'
            self.cursor.execute(sql, (tuple(pk_vals),))
            row = self.cursor.fetchone()
            count = row[0] if row else 0

            if count == len(pk_vals):
                return CommitOutcomeState.COMMITTED
            elif count == 0:
                return CommitOutcomeState.NOT_COMMITTED
            else:
                return CommitOutcomeState.UNKNOWN_COMMIT_OUTCOME
        except Exception:
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
        if self.conn:
            try:
                self.conn.close()
            except Exception:
                pass
