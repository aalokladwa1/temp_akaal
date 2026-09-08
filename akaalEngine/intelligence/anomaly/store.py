"""akaalEngine.intelligence.anomaly.store
===========================================
Bounded, tenant/migration-scoped rolling window of NUMERIC health samples
derived from P7C.13's RuntimeHealthInputs -- never canonical telemetry
itself, never a competing telemetry store. Reuses the caller-supplied SQLite
connection pattern already established by
akaalEngine.intelligence.lifecycle.store.IntelligenceArtifactStore /
akaalEngine.intelligence.evaluation.OutcomeStore; the `intelligence_health_
samples` table is created centrally in akaalPipeline.state.unit_of_work.
SQLiteUnitOfWork.initialize_schema, exactly like those two tables.

Retention is enforced at write time (MAX_SAMPLES_PER_MIGRATION), never
unbounded -- P7C.14 must not become an unbounded time-series database.

Deliberately NOT stored in the same SQLite file/connection as canonical
migration state: a caller-supplied `conn` here is expected to be a dedicated
connection to a small P7C-owned side database (see
akaalPipeline.observability.anomaly_resolver.CanonicalAnomalyResolver, which
opens a sibling file next to the canonical migrations DB). Sharing the
canonical DB's own connection/transaction would risk a same-file writer-lock
deadlock: the anomaly resolver runs INSIDE the same request's still-open
canonical unit-of-work transaction (see akaalPipeline.application.
command_handlers.handle_submit_intelligence_request), so a second write
against that same file before the outer transaction commits can never
succeed. `_ensure_table` below is therefore self-managing, exactly like
akaalPipeline.state.repositories.SQLiteMigrationRepository._ensure_table.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, List, Mapping


@dataclass(frozen=True)
class HealthSample:
    """One bounded numeric snapshot for one (tenant, migration) pair.
    `dimensions` holds only plain numeric/str facts already produced by the
    P7C.13 projector (e.g. throughput_rows_per_sec, cdc_backlog_size,
    cdc_lag_seconds) -- never re-derived from a separate canonical read."""

    sample_id: str
    tenant_id: str
    migration_id: str
    observed_at: str
    dimensions: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.tenant_id or not self.migration_id:
            raise ValueError("HealthSample requires non-empty tenant_id and migration_id")
        object.__setattr__(self, "dimensions", dict(self.dimensions))

    @classmethod
    def new(cls, *, tenant_id: str, migration_id: str, dimensions: Mapping[str, Any], observed_at: str = None) -> "HealthSample":
        return cls(
            sample_id=f"intel-health-sample-{uuid.uuid4().hex}",
            tenant_id=tenant_id,
            migration_id=migration_id,
            observed_at=observed_at or datetime.now(timezone.utc).isoformat(),
            dimensions=dimensions,
        )

    def to_dict(self) -> dict:
        return {
            "sample_id": self.sample_id, "tenant_id": self.tenant_id, "migration_id": self.migration_id,
            "observed_at": self.observed_at, "dimensions": dict(self.dimensions),
        }

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "HealthSample":
        return cls(
            sample_id=row["sample_id"], tenant_id=row["tenant_id"], migration_id=row["migration_id"],
            observed_at=row["observed_at"], dimensions=json.loads(row["dimensions"]) if row["dimensions"] else {},
        )


class HealthSampleStore:
    """Bounded per-migration rolling window. Never grows without limit."""

    MAX_SAMPLES_PER_MIGRATION = 500

    def ensure_table(self, conn: sqlite3.Connection) -> None:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS intelligence_health_samples (
                sample_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                migration_id TEXT NOT NULL,
                observed_at TEXT NOT NULL,
                dimensions TEXT NOT NULL DEFAULT '{}'
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_intel_health_samples_migration "
            "ON intelligence_health_samples (tenant_id, migration_id, observed_at)"
        )

    def save(self, sample: HealthSample, conn: sqlite3.Connection) -> None:
        conn.execute(
            "INSERT INTO intelligence_health_samples (sample_id, tenant_id, migration_id, observed_at, dimensions) "
            "VALUES (?, ?, ?, ?, ?)",
            (sample.sample_id, sample.tenant_id, sample.migration_id, sample.observed_at, json.dumps(dict(sample.dimensions))),
        )
        # Bounded retention: keep only the most recent MAX_SAMPLES_PER_MIGRATION
        # rows for this (tenant, migration) -- enforced at write time so the
        # table can never grow unbounded regardless of caller cadence.
        conn.execute(
            """
            DELETE FROM intelligence_health_samples
            WHERE tenant_id = ? AND migration_id = ? AND sample_id NOT IN (
                SELECT sample_id FROM intelligence_health_samples
                WHERE tenant_id = ? AND migration_id = ?
                ORDER BY observed_at DESC LIMIT ?
            )
            """,
            (sample.tenant_id, sample.migration_id, sample.tenant_id, sample.migration_id, self.MAX_SAMPLES_PER_MIGRATION),
        )

    def list_recent(self, tenant_id: str, migration_id: str, conn: sqlite3.Connection, *, limit: int = 50) -> List[HealthSample]:
        limit = max(1, min(limit, self.MAX_SAMPLES_PER_MIGRATION))
        cur = conn.execute(
            "SELECT * FROM intelligence_health_samples WHERE tenant_id = ? AND migration_id = ? "
            "ORDER BY observed_at DESC LIMIT ?",
            (tenant_id, migration_id, limit),
        )
        # Returned oldest-first -- the natural order for trend/baseline math.
        return list(reversed([HealthSample.from_row(row) for row in cur.fetchall()]))
