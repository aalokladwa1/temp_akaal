"""
Akaal — Risk Analysis Normalization Pipeline Orchestrator Engine
===============================================================
Pipeline orchestrator running Risk analyzers and single-responsibility engines in sequence.
"""

import time
from typing import Tuple, List
from akaal.risk.models.risk_context import RiskContext
from akaal.risk.models.risk_trace import RiskExecutionTrace, RiskTraceStep
from akaal.risk.models.risk_assessment_model import RiskAssessmentModel
from akaal.risk.models.risk_dependency_graph import RiskDependencyGraph
from akaal.risk.models.risk_item import RiskItem
from akaal.risk.registry.analyzer_registry import AnalyzerRegistry

from akaal.risk.engine.compatibility_engine import CompatibilityEngine
from akaal.risk.engine.data_loss_engine import DataLossEngine
from akaal.risk.engine.downtime_engine import DowntimeEngine
from akaal.risk.engine.performance_engine import PerformanceEngine
from akaal.risk.engine.resource_engine import ResourceEngine
from akaal.risk.engine.complexity_engine import ComplexityEngine
from akaal.risk.engine.readiness_engine import ReadinessEngine
from akaal.risk.engine.aggregation_engine import AggregationEngine
from akaal.risk.reporting.risk_report_builder import RiskReportBuilder


class NormalizationEngine:
    """Orchestrates Risk Platform assessment pipeline sequence."""

    def analyze(self, ctx: RiskContext) -> Tuple[RiskAssessmentModel, RiskExecutionTrace]:
        t0 = time.time()
        trace = RiskExecutionTrace(correlation_id=ctx.correlation_id)

        # 1. Run Analyzers
        registry = AnalyzerRegistry(auto_register_defaults=True)
        raw_items: List[RiskItem] = []

        step_idx = 1
        for analyzer in registry._analyzers.values():
            a_t0 = time.time()
            items = analyzer.analyze(ctx)
            a_t1 = time.time()
            raw_items.extend(items)

            trace.add_step(RiskTraceStep(
                analysis_order=step_idx,
                analyzer_or_engine_name=analyzer.analyzer_id,
                target_object_id=ctx.canonical_model.model_signature,
                status="ANALYZED",
                duration_ms=(a_t1 - a_t0) * 1000.0,
                detected_risks_count=len(items),
            ))
            step_idx += 1

        # 2. Aggregation & Deduplication Engine
        agg_engine = AggregationEngine()
        deduped_items, risk_score, evidence_graph = agg_engine.aggregate(raw_items)

        # 3. Engines Execution
        comp_engine = CompatibilityEngine()
        compat_summary = comp_engine.evaluate_compatibility(ctx, deduped_items)

        loss_engine = DataLossEngine()
        loss_summary = loss_engine.evaluate_data_loss(ctx, deduped_items)

        down_engine = DowntimeEngine()
        downtime_estimate = down_engine.estimate_downtime(ctx)

        perf_engine = PerformanceEngine()
        perf_prediction = perf_engine.predict_performance(ctx)

        res_engine = ResourceEngine()
        resource_estimate = res_engine.estimate_resources(ctx)

        cmpx_engine = ComplexityEngine()
        complexity = cmpx_engine.evaluate_complexity(ctx)

        read_engine = ReadinessEngine()
        readiness = read_engine.evaluate_readiness(ctx, deduped_items)

        dep_graph = RiskDependencyGraph()

        t1 = time.time()
        trace.total_trace_duration_ms = (t1 - t0) * 1000.0

        # Build RiskAssessmentModel
        model = RiskReportBuilder.build_model(
            ctx=ctx,
            risk_score=risk_score,
            readiness=readiness,
            complexity=complexity,
            downtime_estimate=downtime_estimate,
            resource_estimate=resource_estimate,
            performance_prediction=perf_prediction,
            evidence_graph=evidence_graph,
            risk_dependency_graph=dep_graph,
            risk_items=deduped_items,
            trace=trace,
        )

        return model, trace
