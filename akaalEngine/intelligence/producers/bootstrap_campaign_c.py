"""akaalEngine.intelligence.producers.bootstrap_campaign_c
============================================================
Registers Campaign C (P7C.13+) producers onto a shared IntelligenceKernel
instance, e.g. the one akaalPipeline.application.unified_caller.
PipelineUnifiedCaller constructs for production use -- the same real
akaalIPC -> akaalPipeline -> akaalEngine.intelligence seam already proven for
Campaign A/B (see akaalEngine.intelligence.producers.bootstrap). Kept in a
separate module from Campaign A/B's bootstrap.py so the owner-frozen P7C
Group 1 registration function is never touched by Group 2 work.

P7C.13 canonical-truth correction: this module NEVER supplies a fallback
resolver that trusts caller-declared operational facts. `runtime_health_
resolver` must be supplied by the caller (in production, akaalPipeline.
application.unified_caller.PipelineUnifiedCaller._build_runtime_health_
resolver, backed by akaalPipeline.observability.runtime_health_resolver.
CanonicalRuntimeHealthResolver -- a genuine read-only projection over
canonical migration/runtime/telemetry/CDC/Fabric state). If no resolver is
supplied, the runtime_health capability is simply NOT registered: a request
for it then fails closed with IntelligenceTaskUnsupportedError ("no producer
registered"), never silently falling back to trusting the caller's own claims
about operational state. Unit tests that need a deterministic fixture
resolver build one directly and pass it here explicitly -- there is no
implicit "test-mode" caller-trusting path reachable through normal production
wiring.
"""

from __future__ import annotations

from typing import Optional

from akaalEngine.intelligence.api import IntelligenceKernel
from akaalEngine.intelligence.models.request import IntelligenceTask
from akaalEngine.intelligence.producers.anomaly_detection import (
    AnomalyDetectionResolver,
    make_anomaly_detection_producer,
)
from akaalEngine.intelligence.producers.finops import FinOpsResolver, make_finops_producer
from akaalEngine.intelligence.producers.forecast_evaluation import make_forecast_evaluation_producer
from akaalEngine.intelligence.producers.forecasting import ForecastResolver, make_forecast_producer
from akaalEngine.intelligence.producers.optimization import ConstraintResolver, make_optimization_producer
from akaalEngine.intelligence.producers.rca import RCAResolver, make_rca_producer
from akaalEngine.intelligence.producers.operator_query import OperatorQueryResolver, make_operator_query_producer
from akaalEngine.intelligence.producers.portfolio import PortfolioResolver, make_portfolio_producer
from akaalEngine.intelligence.producers.remediation import RemediationResolver, make_remediation_producer
from akaalEngine.intelligence.producers.security_risk import SecurityRiskResolver, make_security_risk_producer
from akaalEngine.intelligence.producers.runtime_health import (
    RuntimeHealthResolver,
    make_runtime_health_producer,
)


def register_all_campaign_c_producers(
    kernel: IntelligenceKernel,
    *,
    runtime_health_resolver: Optional[RuntimeHealthResolver] = None,
    anomaly_detection_resolver: Optional[AnomalyDetectionResolver] = None,
    rca_resolver: Optional[RCAResolver] = None,
    forecast_resolver: Optional[ForecastResolver] = None,
    optimization_constraint_resolver: Optional[ConstraintResolver] = None,
    remediation_resolver: Optional[RemediationResolver] = None,
    security_risk_resolver: Optional[SecurityRiskResolver] = None,
    portfolio_resolver: Optional[PortfolioResolver] = None,
    finops_resolver: Optional[FinOpsResolver] = None,
    operator_query_resolver: Optional[OperatorQueryResolver] = None,
) -> None:
    """`runtime_health_resolver`/`anomaly_detection_resolver` -- MUST be backed
    by real canonical authorities when supplied for production use (see module
    docstring). Passing None (the default) means that capability is simply not
    registered -- fail closed, never trust-the-caller-by-default."""
    if runtime_health_resolver is not None:
        kernel.register_producer(
            IntelligenceTask.QUERY,
            make_runtime_health_producer(runtime_health_resolver),
            capability="runtime_health",
        )
    if anomaly_detection_resolver is not None:
        kernel.register_producer(
            IntelligenceTask.ASSESS,
            make_anomaly_detection_producer(anomaly_detection_resolver),
            capability="anomaly_detection",
        )
    if rca_resolver is not None:
        kernel.register_producer(
            IntelligenceTask.EXPLAIN,
            make_rca_producer(rca_resolver),
            capability="root_cause_analysis",
        )
    if forecast_resolver is not None:
        kernel.register_producer(
            IntelligenceTask.FORECAST,
            make_forecast_producer(forecast_resolver),
            capability="operations_forecast",
        )
    # Always registered (unlike the resolvers above): performance optimization
    # over caller-supplied planning parameters works even with no canonical
    # region authorizer configured -- it only refuses when a request actually
    # asserts candidate_regions without one (fail closed on that specific path).
    kernel.register_producer(
        IntelligenceTask.OPTIMIZE,
        make_optimization_producer(optimization_constraint_resolver),
        capability="performance_optimization",
    )
    if remediation_resolver is not None:
        kernel.register_producer(
            IntelligenceTask.RECOMMEND,
            make_remediation_producer(remediation_resolver),
            capability="governed_remediation",
        )
    if security_risk_resolver is not None:
        kernel.register_producer(
            IntelligenceTask.ASSESS,
            make_security_risk_producer(security_risk_resolver),
            capability="security_risk_intelligence",
        )
    if portfolio_resolver is not None:
        kernel.register_producer(
            IntelligenceTask.QUERY,
            make_portfolio_producer(portfolio_resolver),
            capability="portfolio_intelligence",
        )
    if finops_resolver is not None:
        kernel.register_producer(
            IntelligenceTask.FORECAST,
            make_finops_producer(finops_resolver),
            capability="finops_projection",
        )
    if operator_query_resolver is not None:
        kernel.register_producer(
            IntelligenceTask.QUERY,
            make_operator_query_producer(operator_query_resolver),
            capability="operator_query",
        )
    # Always registered: pure deterministic comparison of caller-supplied
    # numbers, no canonical resolution needed.
    kernel.register_producer(
        IntelligenceTask.COMPARE,
        make_forecast_evaluation_producer(),
        capability="forecast_evaluation",
    )
