"""akaalPipeline.observability.forecast_resolver
===================================================
P7C.17 canonical resolver: reuses P7C.13's CanonicalRuntimeHealthResolver for
tenant/plan identity + engine-authority sampling (never a second authority
access path), and additionally samples TelemetryAuthority.get_progress_snapshot
directly for rows_processed/rows_total/rows_per_second -- genuine canonical
facts P7C.13's own RuntimeHealthInputs does not carry (it only exposes the
instantaneous rate, not the total/processed counts needed for an ETA).
"""

from __future__ import annotations

from typing import Any, Optional

from akaalEngine.intelligence.producers.forecasting import ForecastInputs
from akaalEngine.intelligence.producers.runtime_health import make_runtime_health_producer
from akaalEngine.intelligence.models.context import IntelligenceContext
from akaalEngine.intelligence.models.request import IntelligenceRequest, IntelligenceTask
from akaalPipeline.observability.runtime_health_resolver import CanonicalRuntimeHealthResolver
from akaalPipeline.security.context import PipelineActorContext


class CanonicalForecastResolver:
    def __init__(self, health_resolver: CanonicalRuntimeHealthResolver) -> None:
        self._health_resolver = health_resolver

    def resolve(
        self,
        migration_id: str,
        actor: PipelineActorContext,
        *,
        ownership_manager: Optional[Any] = None,
    ) -> ForecastInputs:
        health_inputs = self._health_resolver.resolve(migration_id, actor, ownership_manager=ownership_manager)
        tenant_id = actor.organization_id

        health_producer = make_runtime_health_producer(lambda _req, _ctx: health_inputs)
        probe_request = IntelligenceRequest(
            task=IntelligenceTask.QUERY, tenant_id=tenant_id, subject_type="migration",
            subject_id=migration_id, subject_version="v1", requested_by="p7c17-internal",
            capability="runtime_health",
        )
        probe_context = IntelligenceContext(
            tenant_id=tenant_id, subject_type="migration", subject_id=migration_id, subject_version="v1",
        )
        health_result = health_producer(probe_request, probe_context)
        dims = health_result.data.get("dimensions", {})

        rows_processed = None
        rows_total = None
        rows_per_second = (health_inputs.transport or {}).get("throughput_rows_per_sec")

        runtime_snap, cdc_snap, telemetry_authority = self._health_resolver.sample_engine_authorities()
        if telemetry_authority is not None and hasattr(telemetry_authority, "get_progress_snapshot"):
            try:
                snap = telemetry_authority.get_progress_snapshot(migration_id)
                if snap is not None:
                    rows_processed = getattr(snap, "rows_processed", None)
                    total = getattr(snap, "rows_total", None)
                    rows_total = total if (total is not None and total > 0) else None
                    rows_per_second = getattr(snap, "rows_per_second", rows_per_second)
            except Exception:  # noqa: BLE001 -- degrade to UNKNOWN, never crash the request
                pass

        cdc_backlog_bytes = (cdc_snap or {}).get("backlog_bytes")

        return ForecastInputs(
            migration_id=migration_id,
            rows_processed=rows_processed,
            rows_total=rows_total,
            rows_per_second=rows_per_second,
            cdc_backlog_bytes=cdc_backlog_bytes,
            cdc_generation_rate_bytes_per_sec=None,  # NOT_CURRENTLY_EXPOSED -- see P7C.13 correction.
            cdc_apply_rate_bytes_per_sec=None,  # NOT_CURRENTLY_EXPOSED -- see P7C.13 correction.
            fabric_status=str(dims.get("FABRIC", {}).get("status", "UNKNOWN")),
            validation_status=str(dims.get("VALIDATION", {}).get("status", "UNKNOWN")),
        )
