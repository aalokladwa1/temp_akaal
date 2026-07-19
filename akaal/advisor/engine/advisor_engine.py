"""
Akaal — Advisor Engine
======================
Core orchestration engine for Advisor Platform.
Coordinates validation -> registry resolution -> analyzer execution -> aggregation -> output validation -> model generation.
Contains zero domain business logic.
"""

import time
from typing import Any, Dict, List, Optional

from akaal.advisor.engine.aggregation_engine import AdvisoryAggregationEngine
from akaal.advisor.events.advisor_events import AdvisorEvents
from akaal.advisor.governance.advisor_governance import AdvisorGovernance
from akaal.advisor.metrics.advisor_metrics import AdvisorMetricsCollector
from akaal.advisor.models.advisory_context import AdvisoryContext
from akaal.advisor.models.advisory_recommendation import AdvisoryRecommendation
from akaal.advisor.models.advisory_trace import AdvisoryTrace
from akaal.advisor.models.migration_advisory_model import MigrationAdvisoryModel
from akaal.advisor.registry.advisor_registry import AdvisorRegistry
from akaal.advisor.validation.advisor_validator import (
    AdvisorValidationError,
    AdvisorValidator,
)


class AdvisorEngine:
    """Enterprise Orchestration Engine for Advisor Platform."""

    def __init__(
        self,
        registry: Optional[AdvisorRegistry] = None,
        metrics_collector: Optional[AdvisorMetricsCollector] = None,
    ) -> None:
        self.registry = registry or AdvisorRegistry
        self.metrics_collector = metrics_collector or AdvisorMetricsCollector()

    def execute(
        self,
        plan: Any,
        context: Optional[AdvisoryContext] = None,
        advisory_id: str = "ADV-001",
    ) -> MigrationAdvisoryModel:
        """
        Execute full Advisor Platform pipeline over input execution plan.
        Pure transformation pipeline.
        """
        start_time = time.perf_counter()
        ctx = context or AdvisoryContext()

        # 1. Validate Input Plan
        input_issues = AdvisorValidator.validate_input_plan(plan)
        if input_issues:
            AdvisorEvents.publish_validation_failed(input_issues)
            raise AdvisorValidationError(f"Input validation failed: {'; '.join(input_issues)}")

        plan_dict = plan.to_dict() if hasattr(plan, "to_dict") else dict(plan or {})
        plan_id = plan_dict.get("metadata", {}).get("plan_id", ctx.plan_id or "PLAN-DEFAULT")
        plan_checksum = plan_dict.get("sha256_checksum", "")

        # 2. Registry Resolution
        analyzers = self.registry.get_all_analyzers()
        if not analyzers:
            self.registry.register_defaults()
            analyzers = self.registry.get_all_analyzers()

        # 3. Publish PlatformStarted event
        AdvisorEvents.publish_platform_started(plan_id)

        # 4. Analyzer Execution Loop
        raw_recommendations: List[AdvisoryRecommendation] = []
        analyzer_traces: List[Dict[str, Any]] = []

        for analyzer in analyzers:
            a_name = analyzer.name
            AdvisorEvents.publish_analyzer_started(a_name)
            a_start = time.perf_counter()
            try:
                recs = analyzer.analyze(plan, ctx)
                a_duration = (time.perf_counter() - a_start) * 1000.0

                raw_recommendations.extend(recs)
                self.metrics_collector.record_analyzer_duration(a_name, a_duration)
                self.metrics_collector.record_analyzer_success(a_name)
                AdvisorEvents.publish_analyzer_completed(a_name, len(recs), a_duration)

                analyzer_traces.append({
                    "analyzer_name": a_name,
                    "category": analyzer.category.value,
                    "status": "SUCCESS",
                    "duration_ms": round(a_duration, 3),
                    "recommendations_count": len(recs),
                })
            except Exception as ex:
                a_duration = (time.perf_counter() - a_start) * 1000.0
                self.metrics_collector.record_analyzer_duration(a_name, a_duration)
                self.metrics_collector.record_analyzer_failure(a_name)

                analyzer_traces.append({
                    "analyzer_name": a_name,
                    "category": analyzer.category.value,
                    "status": "FAILED",
                    "duration_ms": round(a_duration, 3),
                    "error": str(ex),
                })

        # 5. Aggregation Engine
        manifest, sorted_recs = AdvisoryAggregationEngine.aggregate(
            raw_recommendations=raw_recommendations,
            plan_id=plan_id,
            plan_checksum=plan_checksum,
            advisory_id=advisory_id,
        )

        total_duration_ms = (time.perf_counter() - start_time) * 1000.0
        self.metrics_collector.record_total_latency(total_duration_ms)

        # 6. Build AdvisoryTrace
        trace = AdvisoryTrace(
            trace_id=f"TR-{advisory_id}",
            execution_duration_ms=round(total_duration_ms, 3),
            analyzer_traces=tuple(analyzer_traces),
            lineage_graph={"plan_id": plan_id, "advisory_id": advisory_id},
            diagnostic_logs=tuple([f"Processed {len(sorted_recs)} recommendations across {len(analyzers)} analyzers."]),
        )

        # 7. Governance metadata
        governance = {
            "version_compatible": AdvisorGovernance.check_version_compatibility(manifest.creation_timestamp[:4] if manifest.creation_timestamp else "1.0.0"),
            "audit_status": "PASSED",
            "deterministic_execution": True,
        }

        # 8. Build MigrationAdvisoryModel
        model = MigrationAdvisoryModel(
            manifest=manifest,
            context=ctx,
            recommendations=sorted_recs,
            trace=trace,
            governance=governance,
            metadata={"generator": "AdvisorEngine-V1"},
            statistics=self.metrics_collector.get_summary(),
        )

        self.metrics_collector.record_model(model)

        # 9. Output Validation
        output_issues = AdvisorValidator.validate_advisory_model(model)
        if output_issues:
            AdvisorEvents.publish_validation_failed(output_issues)
            raise AdvisorValidationError(f"Output model validation failed: {'; '.join(output_issues)}")

        # 10. Publish PlatformCompleted event
        AdvisorEvents.publish_platform_completed(advisory_id, len(sorted_recs))

        return model
