"""akaalPipeline.observability.finops_resolver
=================================================
P7C.20 canonical resolver: reuses the REAL P7C.17 CanonicalForecastResolver
for migration_eta_seconds (never re-derived here); worker_count/
dataset_size_bytes/cost_per_worker_hour come from the caller's OWN planning
parameters (the same class of legitimate caller-supplied input P7C.12/16
already accept -- never an operational-health claim).
"""

from __future__ import annotations

from typing import Any, Mapping, Optional

from akaalEngine.intelligence.producers.finops import FinOpsInputs
from akaalPipeline.observability.forecast_resolver import CanonicalForecastResolver
from akaalPipeline.security.context import PipelineActorContext


class CanonicalFinOpsResolver:
    def __init__(self, forecast_resolver: CanonicalForecastResolver) -> None:
        self._forecast_resolver = forecast_resolver

    def resolve(
        self,
        migration_id: str,
        actor: PipelineActorContext,
        parameters: Mapping[str, Any],
        *,
        ownership_manager: Optional[Any] = None,
    ) -> FinOpsInputs:
        forecast_inputs = self._forecast_resolver.resolve(migration_id, actor, ownership_manager=ownership_manager)

        eta_seconds = None
        if (
            forecast_inputs.rows_total is not None and forecast_inputs.rows_total > 0
            and forecast_inputs.rows_processed is not None
            and forecast_inputs.rows_per_second is not None and forecast_inputs.rows_per_second > 0
        ):
            remaining = max(forecast_inputs.rows_total - forecast_inputs.rows_processed, 0)
            eta_seconds = remaining / forecast_inputs.rows_per_second

        return FinOpsInputs(
            tenant_id=actor.organization_id,
            migration_id=migration_id,
            migration_eta_seconds=eta_seconds,
            dataset_size_bytes=parameters.get("dataset_size_bytes"),
            worker_count=parameters.get("worker_count"),
            cost_per_worker_hour=parameters.get("cost_per_worker_hour"),
        )
