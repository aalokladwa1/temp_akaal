"""
akaalEngine.transport.drivers.vertica
======================================
Canonical Vertica physical Transport driver (P7A Campaign B, provider #40).

`vertica_python` is a real DB-API 2.0 driver (paramstyle 'format' / '%s', ANSI
double-quoted identifiers supported), so the source-read path reuses
`GenericSQLSourceReader` directly. `VerticaTargetWriter` subclasses
`GenericSQLTargetWriter` for a genuinely distinct identity and a real physical
`verify_uncertain_commit` (PK-requery) -- Vertica's MPP commit protocol can leave a
write's outcome ambiguous after a connection reset during COPY/INSERT.

No native COPY bulk-protocol claim is made -- only the executemany() path this driver
actually implements. CDC is not claimed for Vertica (no capture module exists).
"""

from __future__ import annotations

import logging
from typing import Optional, Sequence

from akaalEngine.transport.drivers.generic_sql import GenericSQLSourceReader, GenericSQLTargetWriter
from akaalEngine.transport.models.batch import TransportBatch
from akaalEngine.transport.models.capabilities import (
    CancellationCapability,
    CommitOutcomeState,
    IdempotencyMode,
    LOBMode,
    ProviderCapabilities,
    ResumabilityMode,
)

logger = logging.getLogger("akaalEngine.transport.drivers.vertica")

VERTICA_DEFAULT_PORT = 5433


class VerticaTargetWriter(GenericSQLTargetWriter):
    """Vertica target writer -- reuses GenericSQL's paramstyle-aware executemany() with a
    genuinely distinct identity and a real physical ambiguous-commit verification."""

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

    def verify_uncertain_commit(
        self,
        table_name: str,
        target_schema: str,
        pk_columns: Optional[Sequence[str]],
        batch: TransportBatch,
    ) -> CommitOutcomeState:
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
                tuple(pk_values),
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
            logger.warning(f"[VerticaTargetWriter] verify_uncertain_commit physical check failed: {exc}")
            return CommitOutcomeState.UNKNOWN_COMMIT_OUTCOME


VerticaSourceReader = GenericSQLSourceReader
