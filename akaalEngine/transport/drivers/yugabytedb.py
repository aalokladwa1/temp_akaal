"""
akaalEngine.transport.drivers.yugabytedb
===========================================
Canonical YugabyteDB physical Transport driver (P7A Campaign B independence hardening).

YSQL is PostgreSQL-wire-compatible (same reasoning as CockroachDBTargetWriter), reused with
a genuinely distinct identity and YugabyteDB-specific defaults/ambiguous-commit verification.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Sequence

from akaalEngine.transport.drivers.postgres import PostgreSQLTargetWriter, _HAS_PG
from akaalEngine.transport.models.batch import TransportBatch
from akaalEngine.transport.models.capabilities import CommitOutcomeState

logger = logging.getLogger("akaalEngine.transport.drivers.yugabytedb")

if _HAS_PG:
    import psycopg2


class YugabyteDBTargetWriter(PostgreSQLTargetWriter):
    """YugabyteDB target writer -- reuses PostgreSQL-wire-compatible execute_values logic
    with a genuinely distinct identity and YugabyteDB-specific ambiguous-commit verification."""

    def _connect(self) -> None:
        if not _HAS_PG:
            from akaalEngine.transport.models.errors import TransportCapabilityError
            raise TransportCapabilityError("psycopg2 library is not installed for YugabyteDBTargetWriter driver.")

        pg_keys = {"host", "port", "user", "password", "dbname", "sslmode", "connect_timeout", "options"}
        raw_params = dict(self.params)
        user_val = raw_params.pop("user", None) or raw_params.pop("username", None)
        dbname_val = raw_params.pop("dbname", None) or raw_params.pop("database", None) or raw_params.pop("database_name", None)

        pg_params: Dict[str, Any] = {"port": 5433}  # YugabyteDB's default YSQL port
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
        """Real physical verification against the target table by primary key -- see
        CockroachDBTargetWriter.verify_uncertain_commit for the identical rationale."""
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
            logger.warning(f"[YugabyteDBTargetWriter] verify_uncertain_commit physical check failed: {exc}")
            return CommitOutcomeState.UNKNOWN_COMMIT_OUTCOME
