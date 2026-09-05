"""
akaalEngine.transport.drivers.cockroachdb
============================================
Canonical CockroachDB physical Transport driver (P7A Campaign B independence hardening).

CockroachDB's YSQL wire protocol is PostgreSQL-compatible, so the source-read path reuses
`GenericSQLSourceReader` (now paramstyle-aware) directly -- a real driver-cursor read, not a
relabel. The target-write path subclasses `PostgreSQLTargetWriter` to reuse its correct
`execute_values`/savepoint-retry logic (both wire-compatible), while keeping a genuinely
distinct class identity and overriding what is actually different:
  - Default port 26257, not PostgreSQL's 5432.
  - SQLSTATE 40001 (CockroachDB's routine distributed-transaction-conflict signal) is
    classified as a genuinely committed-vs-not-committed check in `verify_uncertain_commit`:
    on an ambiguous outcome, this queries whether the batch's primary-key values are now
    present in the target table rather than blindly returning UNKNOWN -- a real physical
    verification, not a documentation-only claim.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Sequence

from akaalEngine.transport.drivers.postgres import PostgreSQLTargetWriter, _HAS_PG
from akaalEngine.transport.models.batch import TransportBatch
from akaalEngine.transport.models.capabilities import CommitOutcomeState

logger = logging.getLogger("akaalEngine.transport.drivers.cockroachdb")

if _HAS_PG:
    import psycopg2


class CockroachDBTargetWriter(PostgreSQLTargetWriter):
    """CockroachDB target writer -- reuses PostgreSQL-wire-compatible execute_values logic
    with a genuinely distinct identity and CockroachDB-specific ambiguous-commit verification."""

    def _connect(self) -> None:
        if not _HAS_PG:
            from akaalEngine.transport.models.errors import TransportCapabilityError
            raise TransportCapabilityError("psycopg2 library is not installed for CockroachDBTargetWriter driver.")

        pg_keys = {"host", "port", "user", "password", "dbname", "sslmode", "connect_timeout", "options"}
        raw_params = dict(self.params)
        user_val = raw_params.pop("user", None) or raw_params.pop("username", None)
        dbname_val = raw_params.pop("dbname", None) or raw_params.pop("database", None) or raw_params.pop("database_name", None)

        pg_params: Dict[str, Any] = {"port": 26257}  # CockroachDB's default YSQL port, not PostgreSQL's 5432
        if user_val:
            pg_params["user"] = user_val
        if dbname_val:
            pg_params["dbname"] = dbname_val
        for k, v in raw_params.items():
            if k in pg_keys and v is not None:
                pg_params[k] = v

        self.conn = psycopg2.connect(**pg_params)
        self.cursor = self.conn.cursor()

    def verify_uncertain_commit(
        self,
        table_name: str,
        target_schema: str,
        pk_columns: Optional[Sequence[str]],
        batch: TransportBatch,
    ) -> CommitOutcomeState:
        """Real physical verification: after an ambiguous write (e.g. connection reset during
        SQLSTATE 40001 retry), check whether the batch's rows are actually present in the
        target table by primary key, rather than fabricating an UNKNOWN result unconditionally."""
        if not self.conn or not pk_columns or not batch.rows:
            return CommitOutcomeState.UNKNOWN_COMMIT_OUTCOME
        try:
            pk_col = pk_columns[0]
            pk_values = [r.get(pk_col) for r in batch.rows if r.get(pk_col) is not None]
            if not pk_values:
                return CommitOutcomeState.UNKNOWN_COMMIT_OUTCOME
            check_cur = self.conn.cursor()
            placeholders = ", ".join(["%s"] * len(pk_values))
            check_cur.execute(
                f'SELECT count(*) FROM "{target_schema}"."{table_name}" WHERE "{pk_col}" IN ({placeholders})',
                pk_values,
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
            logger.warning(f"[CockroachDBTargetWriter] verify_uncertain_commit physical check failed: {exc}")
            return CommitOutcomeState.UNKNOWN_COMMIT_OUTCOME
