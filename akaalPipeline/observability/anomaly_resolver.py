"""akaalPipeline.observability.anomaly_resolver
=================================================
P7C.14 canonical resolver: composes the REAL P7C.13
CanonicalRuntimeHealthResolver (never re-deriving tenant/migration/canonical
authority logic) with a bounded, P7C-owned history
(akaalEngine.intelligence.anomaly.store.HealthSampleStore) to build
AnomalyDetectionInputs. Reuses P7C.13's own runtime_health producer function
to compute per-dimension statuses (FABRIC/VALIDATION precedence) rather than
re-implementing that evaluation logic -- zero duplicate authority.
"""

from __future__ import annotations

import sqlite3
from typing import Any, Optional

from akaalEngine.intelligence.anomaly.store import HealthSample, HealthSampleStore
from akaalEngine.intelligence.models.context import IntelligenceContext
from akaalEngine.intelligence.models.request import IntelligenceRequest, IntelligenceTask
from akaalEngine.intelligence.producers.anomaly_detection import AnomalyDetectionInputs
from akaalEngine.intelligence.producers.runtime_health import make_runtime_health_producer
from akaalPipeline.observability.runtime_health_resolver import CanonicalRuntimeHealthResolver
from akaalPipeline.security.context import PipelineActorContext


class CanonicalAnomalyResolver:
    """Read-mostly (writes only its OWN bounded sample history, never
    canonical state) projection adapter for P7C.14."""

    def __init__(
        self,
        health_resolver: CanonicalRuntimeHealthResolver,
        db_path: str,
        sample_store: Optional[HealthSampleStore] = None,
        history_window: int = 30,
    ) -> None:
        self._health_resolver = health_resolver
        # Deliberately a SIBLING file, never the canonical migrations DB file/
        # connection: this resolver runs INSIDE the same request's still-open
        # canonical unit-of-work transaction (see module docstring on
        # akaalEngine.intelligence.anomaly.store) -- writing to the same file
        # here would deadlock against that open transaction.
        self._sample_db_path = f"{db_path}.p7c14_health_samples.db"
        self._sample_store = sample_store or HealthSampleStore()
        self._history_window = history_window

    @property
    def health_resolver(self) -> CanonicalRuntimeHealthResolver:
        return self._health_resolver

    def resolve(
        self,
        migration_id: str,
        actor: PipelineActorContext,
        *,
        ownership_manager: Optional[Any] = None,
    ) -> AnomalyDetectionInputs:
        # Tenant/plan identity and canonical resource-scope enforcement happen
        # entirely inside CanonicalRuntimeHealthResolver.resolve -- this class
        # performs no independent tenant check (would risk drift from P7C.13's
        # own anti-enumeration-safe enforcement).
        health_inputs = self._health_resolver.resolve(migration_id, actor, ownership_manager=ownership_manager)
        tenant_id = actor.organization_id

        # Reuse the EXACT P7C.13 dimension-evaluation code path (never
        # reimplemented here) to get FABRIC/VALIDATION status for precedence.
        health_producer = make_runtime_health_producer(lambda _req, _ctx: health_inputs)
        probe_request = IntelligenceRequest(
            task=IntelligenceTask.QUERY, tenant_id=tenant_id, subject_type="migration",
            subject_id=migration_id, subject_version="v1", requested_by="p7c14-internal",
            capability="runtime_health",
        )
        probe_context = IntelligenceContext(
            tenant_id=tenant_id, subject_type="migration", subject_id=migration_id, subject_version="v1",
        )
        health_result = health_producer(probe_request, probe_context)

        current_dimensions = {
            "throughput_rows_per_sec": (health_inputs.transport or {}).get("throughput_rows_per_sec"),
            "cdc_backlog_size": (health_inputs.cdc or {}).get("backlog_size"),
            "cdc_lag_seconds": (health_inputs.cdc or {}).get("lag_seconds"),
        }

        conn = sqlite3.connect(self._sample_db_path)
        conn.row_factory = sqlite3.Row
        try:
            self._sample_store.ensure_table(conn)
            historical = self._sample_store.list_recent(tenant_id, migration_id, conn, limit=self._history_window)
            sample = HealthSample.new(tenant_id=tenant_id, migration_id=migration_id, dimensions=current_dimensions)
            self._sample_store.save(sample, conn)
            conn.commit()
        finally:
            conn.close()

        return AnomalyDetectionInputs(
            tenant_id=tenant_id,
            migration_id=migration_id,
            current_dimensions=current_dimensions,
            historical_dimensions=[h.dimensions for h in historical],
            runtime_health_overall_status=str(health_result.data.get("overall_status", "UNKNOWN")),
            runtime_health_dimensions=health_result.data.get("dimensions", {}),
        )
