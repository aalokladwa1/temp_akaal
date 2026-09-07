"""akaalPipeline.observability.operator_query_resolver
=========================================================
P7C.21 canonical resolver: reuses the REAL P7C.13/14/15/17/18/19/20/22
resolvers and their own producer functions to gather already-computed
grounded summaries -- never recomputes any of them independently.
"""

from __future__ import annotations

from typing import Any, Mapping, Optional

from akaalEngine.intelligence.models.context import IntelligenceContext
from akaalEngine.intelligence.models.request import IntelligenceRequest, IntelligenceTask
from akaalEngine.intelligence.producers.anomaly_detection import make_anomaly_detection_producer
from akaalEngine.intelligence.producers.finops import make_finops_producer
from akaalEngine.intelligence.producers.operator_query import OperatorQueryInputs
from akaalEngine.intelligence.producers.portfolio import make_portfolio_producer
from akaalEngine.intelligence.producers.rca import make_rca_producer
from akaalEngine.intelligence.producers.remediation import make_remediation_producer
from akaalEngine.intelligence.producers.runtime_health import make_runtime_health_producer
from akaalPipeline.observability.finops_resolver import CanonicalFinOpsResolver
from akaalPipeline.observability.forecast_resolver import CanonicalForecastResolver
from akaalPipeline.observability.portfolio_resolver import CanonicalPortfolioResolver
from akaalPipeline.observability.remediation_resolver import CanonicalRemediationResolver
from akaalPipeline.security.context import PipelineActorContext


class CanonicalOperatorQueryResolver:
    def __init__(
        self,
        remediation_resolver: CanonicalRemediationResolver,
        forecast_resolver: CanonicalForecastResolver,
        finops_resolver: CanonicalFinOpsResolver,
        portfolio_resolver: CanonicalPortfolioResolver,
    ) -> None:
        self._remediation_resolver = remediation_resolver
        self._forecast_resolver = forecast_resolver
        self._finops_resolver = finops_resolver
        self._portfolio_resolver = portfolio_resolver

    def resolve(
        self,
        migration_id: str,
        actor: PipelineActorContext,
        parameters: Mapping[str, Any],
        *,
        ownership_manager: Optional[Any] = None,
    ) -> OperatorQueryInputs:
        tenant_id = actor.organization_id

        def _probe(task: IntelligenceTask, capability: str):
            return (
                IntelligenceRequest(
                    task=task, tenant_id=tenant_id, subject_type="migration", subject_id=migration_id,
                    subject_version="v1", requested_by="p7c21-internal", capability=capability,
                ),
                IntelligenceContext(tenant_id=tenant_id, subject_type="migration", subject_id=migration_id, subject_version="v1"),
            )

        # RCA resolver chain already reaches anomaly + health; reuse it once.
        rca_impl = self._remediation_resolver.rca_resolver  # same chain remediation already built
        rca_inputs = rca_impl.resolve(migration_id, actor, ownership_manager=ownership_manager)
        anomaly_inputs = rca_impl.anomaly_resolver.resolve(migration_id, actor, ownership_manager=ownership_manager)
        health_inputs = rca_impl.anomaly_resolver.health_resolver.resolve(migration_id, actor, ownership_manager=ownership_manager)

        health_req, health_ctx = _probe(IntelligenceTask.QUERY, "runtime_health")
        health_result = make_runtime_health_producer(lambda _r, _c: health_inputs)(health_req, health_ctx)

        anomaly_req, anomaly_ctx = _probe(IntelligenceTask.ASSESS, "anomaly_detection")
        anomaly_result = make_anomaly_detection_producer(lambda _r, _c: anomaly_inputs)(anomaly_req, anomaly_ctx)

        rca_req, rca_ctx = _probe(IntelligenceTask.EXPLAIN, "root_cause_analysis")
        rca_result = make_rca_producer(lambda _r, _c: rca_inputs)(rca_req, rca_ctx)

        forecast_inputs = self._forecast_resolver.resolve(migration_id, actor, ownership_manager=ownership_manager)
        from akaalEngine.intelligence.producers.forecasting import make_forecast_producer

        forecast_req, forecast_ctx = _probe(IntelligenceTask.FORECAST, "operations_forecast")
        forecast_result = make_forecast_producer(lambda _r, _c: forecast_inputs)(forecast_req, forecast_ctx)

        remediation_inputs = self._remediation_resolver.resolve(migration_id, actor, ownership_manager=ownership_manager)
        remediation_req, remediation_ctx = _probe(IntelligenceTask.RECOMMEND, "governed_remediation")
        remediation_result = make_remediation_producer(lambda _r, _c: remediation_inputs)(remediation_req, remediation_ctx)

        # FinOps: only computed if the caller supplied planning inputs
        # (same "what-if" convention as intelligence.submit's own finops_projection
        # capability) -- otherwise finops_summary stays None (honest "no scenario given").
        finops_summary = None
        if any(k in parameters for k in ("cost_per_worker_hour", "worker_count", "dataset_size_bytes")):
            finops_inputs_base = self._finops_resolver.resolve(migration_id, actor, ownership_manager=ownership_manager)
            from dataclasses import replace

            finops_inputs = replace(
                finops_inputs_base,
                dataset_size_bytes=parameters.get("dataset_size_bytes", finops_inputs_base.dataset_size_bytes),
                worker_count=parameters.get("worker_count", finops_inputs_base.worker_count),
                cost_per_worker_hour=parameters.get("cost_per_worker_hour", finops_inputs_base.cost_per_worker_hour),
            )
            finops_req, finops_ctx = _probe(IntelligenceTask.FORECAST, "finops_projection")
            finops_result = make_finops_producer(lambda _r, _c: finops_inputs)(finops_req, finops_ctx)
            finops_summary = finops_result.summary

        # Portfolio: tenant-wide, bounded to a small page for a conversational answer.
        portfolio_inputs = self._portfolio_resolver.resolve(actor, ownership_manager=ownership_manager, limit=20)
        portfolio_req, portfolio_ctx = _probe(IntelligenceTask.QUERY, "portfolio_intelligence")
        portfolio_result = make_portfolio_producer(lambda _r, _c: portfolio_inputs)(portfolio_req, portfolio_ctx)

        return OperatorQueryInputs(
            migration_id=migration_id,
            health_summary=health_result.summary,
            anomaly_summary=anomaly_result.summary,
            rca_summary=rca_result.summary,
            rca_supporting_facts="; ".join(rca_result.explanation.supporting_facts) or None,
            rca_invalidation_condition=rca_result.data.get("invalidation_condition") or None,
            forecast_summary=forecast_result.summary,
            remediation_summary=remediation_result.summary,
            finops_summary=finops_summary,
            portfolio_summary=portfolio_result.summary,
        )
