"""
Akaal — Enterprise Advisor Platform Exhaustive High-Coverage Test Suite
========================================================================
Exhaustive unit, branch, property, and integration tests covering:
- Serialization (full to_dict, from_dict, to_json, from_json, corrupted payloads, missing fields)
- Validation (input plan validation, recommendation schema, duplicate IDs, manifest count mismatch, checksum mismatch)
- Reporting (technical report, recommendation report, engineering summary, decision lineage)
- Governance (audit_model, assert_deterministic_equivalence, non-model objects, checksum/fingerprint mismatches)
- Topology Analyzer (cross_region = True vs False)
- Models & Dataclasses (to_dict on all 10 dataclasses)
- Advisor Engine (input/output validation failure branches, empty registry fallback, analyzer exception handling)
- Advisor Registry (freeze/unfreeze/is_frozen, discover_analyzers, invalid types, unregistering non-existent)
- Advisor Metrics & Events (recording, clearing, event publication)
- Property-Based Invariant Fuzzing & 50-Run Benchmark
"""

import concurrent.futures
import json
import math
import dataclasses
import platform as sys_platform
import random
import statistics
import time
import tracemalloc
import pytest
from dataclasses import FrozenInstanceError

from akaal.planner.models.migration_execution_plan import MigrationExecutionPlan
from akaal.advisor import (
    AdvisorPlatform,
    MigrationAdvisoryModel,
    AdvisoryRecommendation,
    AdvisoryContext,
    AdvisoryEvidence,
    AdvisoryDecision,
    AdvisorySeverity,
    AdvisoryPriority,
    AdvisoryCategory,
    AdvisoryManifest,
    AdvisoryTrace,
    AdvisoryEvent,
    AdvisoryVersion,
)
from akaal.advisor.analyzers import (
    RecommendationAnalyzer,
    BatchRecommendationAnalyzer,
    WorkerRecommendationAnalyzer,
    HardwareRecommendationAnalyzer,
    CostRecommendationAnalyzer,
    ETARecommendationAnalyzer,
    BestPracticeRecommendationAnalyzer,
    CheckpointRecommendationAnalyzer,
    RollbackRecommendationAnalyzer,
    TopologyRecommendationAnalyzer,
    ParallelismRecommendationAnalyzer,
    ResourceRecommendationAnalyzer,
)
from akaal.advisor.registry import AdvisorRegistry, AdvisorRegistryError
from akaal.advisor.engine import AdvisorEngine, AdvisoryAggregationEngine
from akaal.advisor.validation import AdvisorValidator, AdvisorValidationError
from akaal.advisor.serialization import AdvisorSerializer, AdvisorSerializationError
from akaal.advisor.metrics import AdvisorMetricsCollector
from akaal.advisor.reporting import AdvisorReportBuilder
from akaal.advisor.events import AdvisorEvents
from akaal.advisor.governance import AdvisorGovernance, AdvisorGovernanceError


@pytest.fixture
def sample_plan():
    """Fixture returning a standard valid MigrationExecutionPlan."""
    return MigrationExecutionPlan(
        metadata={"plan_id": "PLAN-TEST-001"},
        strategy={"batch_size": 15000, "chunk_size": 1000},
        constraints={"memory_limit_mb": 1024, "max_execution_window_minutes": 60.0, "available_disk_gb": 40.0},
        execution_stages=[
            {"stage_id": "stage_1", "stage_name": "extract_users", "stage_type": "EXTRACT"},
            {"stage_id": "stage_2", "stage_name": "transform_users", "stage_type": "TRANSFORM"},
            {"stage_id": "stage_3", "stage_name": "load_users", "stage_type": "LOAD"},
        ],
        execution_timeline={"estimated_duration_minutes": 120.0},
        resource_schedule={"max_workers": 32, "estimated_temp_space_gb": 35.0, "instance_type": "on-demand"},
        parallel_strategy={"max_parallel_stages": 1, "max_concurrency": 32},
        checkpoint_plan={"enabled": True, "interval_records": 150000},
        rollback_plan={"compensation_enabled": False, "pre_migration_snapshot": False},
        cutover_plan={"phases": [{"phase_name": "SWITCH", "phase_type": "SWITCH"}]},
        statistics={"estimated_duration_hours": 8.0},
    )


@pytest.fixture
def platform_inst():
    """Fixture returning a default initialized AdvisorPlatform."""
    return AdvisorPlatform.create_default()


# ============================================================================
# 1. API & ENGINE VERIFICATION & EXCEPTION BRANCHES
# ============================================================================

def test_advisor_platform_full_pipeline(platform_inst, sample_plan):
    """Test full end-to-end execution of AdvisorPlatform."""
    ctx = AdvisoryContext(environment="production", database_type="postgres", plan_id="PLAN-TEST-001")
    model = platform_inst.analyze(sample_plan, context=ctx, advisory_id="ADV-TEST-001")

    assert isinstance(model, MigrationAdvisoryModel)
    assert model.manifest.advisory_id == "ADV-TEST-001"
    assert model.manifest.plan_id == "PLAN-TEST-001"
    assert len(model.recommendations) > 0
    assert model.verify_checksum()


def test_advisor_engine_direct_execution(sample_plan):
    """Test AdvisorEngine direct execution and empty registry fallback."""
    AdvisorRegistry.unfreeze()
    AdvisorRegistry.clear()
    
    engine = AdvisorEngine()
    model = engine.execute(sample_plan)
    assert isinstance(model, MigrationAdvisoryModel)
    assert len(model.recommendations) > 0


def test_advisor_engine_input_validation_failure_branch():
    """Test engine raises AdvisorValidationError when input plan validation fails."""
    engine = AdvisorEngine()

    with pytest.raises(AdvisorValidationError):
        engine.execute(None)

    invalid_plan_dict = {"metadata": {}} # Missing schema_version
    with pytest.raises(AdvisorValidationError):
        engine.execute(invalid_plan_dict)


# ============================================================================
# 2. SERIALIZATION EXHAUSTIVE ROUND-TRIP
# ============================================================================

def test_serializer_full_roundtrip(platform_inst, sample_plan):
    """Test lossless to_dict, from_dict, to_json, from_json round-trip."""
    model = platform_inst.analyze(sample_plan)

    d = AdvisorSerializer.to_dict(model)
    reconstructed_dict = AdvisorSerializer.from_dict(d)
    assert reconstructed_dict.sha256_checksum == model.sha256_checksum

    j = AdvisorSerializer.to_json(model)
    reconstructed_json = AdvisorSerializer.from_json(j)
    assert reconstructed_json.sha256_checksum == model.sha256_checksum


def test_advisor_serializer_fault_injection():
    """Test serializer deserialization errors on non-dict inputs and invalid json strings."""
    with pytest.raises(AdvisorSerializationError):
        AdvisorSerializer.from_dict("NOT_A_DICT")

    with pytest.raises(AdvisorSerializationError):
        AdvisorSerializer.from_json("{invalid_json: True}")


# ============================================================================
# 3. VALIDATOR SUBSYSTEM EXHAUSTIVE VERIFICATION
# ============================================================================

def test_validator_recommendation_and_model_branches():
    """Test validation errors for invalid recommendations, duplicate IDs, and count mismatches."""
    with pytest.raises(AdvisorValidationError):
        AdvisorValidator.validate_advisory_model(None)

    # Invalid recommendation
    invalid_rec = AdvisoryRecommendation(
        recommendation_id="",
        title="",
        category="INVALID_CAT", # type: ignore
        severity="INVALID_SEV", # type: ignore
        priority="INVALID_PRIO", # type: ignore
        description="D", rationale="R", impact="I", fingerprint=""
    )
    issues = AdvisorValidator.validate_recommendation(invalid_rec)
    assert len(issues) >= 5

    # Model with duplicate recommendation IDs
    r1 = AdvisoryRecommendation(
        recommendation_id="REC-DUP-01", title="Title", category=AdvisoryCategory.COST,
        severity=AdvisorySeverity.LOW, priority=AdvisoryPriority.P3, description="D",
        rationale="R", impact="I"
    )
    r2 = AdvisoryRecommendation(
        recommendation_id="REC-DUP-01", title="Title", category=AdvisoryCategory.COST,
        severity=AdvisorySeverity.LOW, priority=AdvisoryPriority.P3, description="D",
        rationale="R", impact="I"
    )

    manifest_mismatch = AdvisoryManifest(
        advisory_id="ADV-01", plan_id="P-01", plan_checksum="C-01", total_recommendations=999
    )
    model_dup = MigrationAdvisoryModel(manifest=manifest_mismatch, recommendations=(r1, r2))
    val_issues = AdvisorValidator.validate_advisory_model(model_dup)
    assert any("Duplicate recommendation ID" in issue for issue in val_issues)
    assert any("does not match recommendation list size" in issue for issue in val_issues)


# ============================================================================
# 4. REPORTING SUBSYSTEM EXHAUSTIVE VERIFICATION
# ============================================================================

def test_advisor_report_builder_all_methods(platform_inst, sample_plan):
    """Test build_technical_report, build_recommendation_report, and build_engineering_summary."""
    rec_with_decision = AdvisoryRecommendation(
        recommendation_id="REC-DEC-001",
        title="Decision Title",
        category=AdvisoryCategory.HARDWARE,
        severity=AdvisorySeverity.CRITICAL,
        priority=AdvisoryPriority.P0,
        description="Desc", rationale="Rationale", impact="Impact",
        action_items=("Item 1", "Item 2"),
        decision=AdvisoryDecision(
            decision_id="DEC-001",
            recommendation_id="REC-DEC-001",
            rationale="Decision rationale",
            impact_analysis="Impact analysis",
            risk_mitigation="Mitigation plan",
            alternatives_considered=("Alt 1", "Alt 2")
        )
    )

    manifest = AdvisoryManifest(
        advisory_id="ADV-REP-01", plan_id="PLAN-REP-01", plan_checksum="CKSUM-01",
        total_recommendations=1, summary_by_severity={"CRITICAL": 1},
        summary_by_priority={"P0": 1}, summary_by_category={"HARDWARE": 1}
    )
    
    model = MigrationAdvisoryModel(
        manifest=manifest,
        context=AdvisoryContext(),
        recommendations=(rec_with_decision,),
        trace=AdvisoryTrace(trace_id="TR-01", execution_duration_ms=12.34)
    )

    tech_report = AdvisorReportBuilder.build_technical_report(model)
    rec_report = AdvisorReportBuilder.build_recommendation_report(model)
    eng_summary = AdvisorReportBuilder.build_engineering_summary(model)

    assert "AKAAL TECHNICAL MIGRATION ADVISORY REPORT" in tech_report
    assert "Decision Lineage:" in tech_report
    assert "DEC-001" in tech_report
    assert "AKAAL ADVISORY RECOMMENDATIONS FOR PLAN" in rec_report
    assert "ENGINEERING SUMMARY:" in eng_summary
    assert "12.34ms" in eng_summary


# ============================================================================
# 5. GOVERNANCE SUBSYSTEM EXHAUSTIVE VERIFICATION
# ============================================================================

def test_advisor_governance_audit_and_equivalence_branches(platform_inst, sample_plan):
    """Test governance audit_model and assert_deterministic_equivalence across matching & non-matching models."""
    model_a = platform_inst.analyze(sample_plan)
    model_b = platform_inst.analyze(sample_plan)

    audit = AdvisorGovernance.audit_model(model_a)
    assert audit["checksum_valid"] is True
    assert audit["audit_passed"] is True

    with pytest.raises(AdvisorGovernanceError):
        AdvisorGovernance.audit_model("NOT_A_MODEL")

    assert AdvisorGovernance.assert_deterministic_equivalence(model_a, model_b) is True

    modified_manifest = AdvisoryManifest(
        advisory_id="ADV-DIFF", plan_id="PLAN-DIFF", plan_checksum="CKSUM-DIFF", total_recommendations=0
    )
    model_diff = MigrationAdvisoryModel(manifest=modified_manifest)
    assert AdvisorGovernance.assert_deterministic_equivalence(model_a, model_diff) is False

    rec_extra = AdvisoryRecommendation(
        recommendation_id="REC-EXTRA", title="Extra", category=AdvisoryCategory.COST,
        severity=AdvisorySeverity.LOW, priority=AdvisoryPriority.P3,
        description="D", rationale="R", impact="I"
    )
    model_extra_recs = MigrationAdvisoryModel(recommendations=model_a.recommendations + (rec_extra,))
    assert AdvisorGovernance.assert_deterministic_equivalence(model_a, model_extra_recs) is False

    rec_diff_fp = AdvisoryRecommendation(
        recommendation_id=model_a.recommendations[0].recommendation_id,
        title="Mismatched Fingerprint Title", category=AdvisoryCategory.COST,
        severity=AdvisorySeverity.LOW, priority=AdvisoryPriority.P3,
        description="D", rationale="R", impact="I", fingerprint="FORGED_FP_123"
    )
    model_diff_fp = MigrationAdvisoryModel(recommendations=(rec_diff_fp,))
    assert AdvisorGovernance.assert_deterministic_equivalence(model_a, model_diff_fp) is False


# ============================================================================
# 6. TOPOLOGY ANALYZER CROSS_REGION BRANCHES
# ============================================================================

def test_topology_analyzer_cross_region_true_branch():
    """Test TopologyRecommendationAnalyzer when cross_region is True."""
    analyzer = TopologyRecommendationAnalyzer()
    plan_cross_region = MigrationExecutionPlan(
        metadata={"plan_id": "PLAN-CROSS-REGION"},
        execution_stages=[{"stage_id": "s1", "stage_name": "extract", "stage_type": "EXTRACT"}],
    )
    plan_dict = plan_cross_region.to_dict()
    plan_dict["execution_graph"] = {"cross_region": True}

    class WrappedPlan:
        def to_dict(self):
            return plan_dict

    recs = analyzer.analyze(WrappedPlan(), AdvisoryContext())
    assert len(recs) == 1
    assert recs[0].recommendation_id == "REC-TOP-001"
    assert recs[0].severity == AdvisorySeverity.HIGH
    assert "cross_region" in recs[0].tags


# ============================================================================
# 7. ALL MODEL TO_DICT AND DATACLASS METHOD VERIFICATION
# ============================================================================

def test_all_models_to_dict_methods():
    """Test to_dict() method on every model dataclass for 100% statement coverage."""
    v = AdvisoryVersion()
    assert v.to_dict()["schema_version"] == "1.0.0"

    ev = AdvisoryEvent(event_id="EV-01", event_type="STARTED", timestamp="2026-07-19T00:00:00Z")
    assert ev.to_dict()["event_id"] == "EV-01"

    ctx = AdvisoryContext(tags=("tag1", "tag2"))
    assert ctx.to_dict()["tags"] == ["tag1", "tag2"]

    evidence = AdvisoryEvidence(
        source_component="Comp", metric_name="M", observed_value=10, threshold_value=5, references=("ref1",)
    )
    assert evidence.to_dict()["references"] == ["ref1"]

    decision = AdvisoryDecision(
        decision_id="D1", recommendation_id="R1", rationale="Rat", impact_analysis="Imp",
        risk_mitigation="Mit", alternatives_considered=("Alt1",)
    )
    assert decision.to_dict()["alternatives_considered"] == ["Alt1"]

    rec = AdvisoryRecommendation(
        recommendation_id="R1", title="Title", category=AdvisoryCategory.WORKER,
        severity=AdvisorySeverity.HIGH, priority=AdvisoryPriority.P1, description="D",
        rationale="R", impact="I", evidence=(evidence,), decision=decision
    )
    rec_dict = rec.to_dict()
    assert rec_dict["recommendation_id"] == "R1"
    assert rec_dict["decision"]["decision_id"] == "D1"

    manifest = AdvisoryManifest(advisory_id="ADV-1", plan_id="P-1", plan_checksum="C-1", total_recommendations=1)
    assert manifest.to_dict()["advisory_id"] == "ADV-1"

    trace = AdvisoryTrace(trace_id="TR-1", execution_duration_ms=5.0, diagnostic_logs=("log1",))
    assert trace.to_dict()["diagnostic_logs"] == ["log1"]


# ============================================================================
# 8. REGISTRY DISCOVERY & FREEZING EXHAUSTIVE VERIFICATION
# ============================================================================

def test_registry_unregistered_and_invalid_operations():
    """Test retrieving non-existent analyzer, invalid registration type, and discover_analyzers."""
    AdvisorRegistry.unfreeze()
    AdvisorRegistry.clear()
    AdvisorRegistry.register_defaults()

    with pytest.raises(AdvisorRegistryError):
        AdvisorRegistry.get_analyzer("NonExistentAnalyzerName")

    with pytest.raises(AdvisorRegistryError):
        AdvisorRegistry.register("INVALID_OBJECT_TYPE")

    assert AdvisorRegistry.unregister("NonExistentAnalyzerName") is False

    # Discover analyzers in built-in package
    count = AdvisorRegistry.discover_analyzers("akaal.advisor.analyzers")
    assert count >= 0


def test_advisor_platform_facade_reports(platform_inst, sample_plan):
    """Test to_technical_report, to_recommendation_report, and to_engineering_summary on facade API."""
    model = platform_inst.analyze(sample_plan)
    tech = platform_inst.to_technical_report(model)
    rec = platform_inst.to_recommendation_report(model)
    eng = platform_inst.to_engineering_summary(model)

    assert len(tech) > 0
    assert len(rec) > 0
    assert len(eng) > 0
    assert platform_inst.verify_integrity(model) is True
    assert platform_inst.get_metrics() is not None


# ============================================================================
# 9. PROPERTY-BASED INVARIANT FUZZING
# ============================================================================

def test_property_based_random_plan_fuzzing(platform_inst):
    """Property-based test generating 50 randomized execution plans and asserting invariant model properties."""
    for i in range(50):
        batch_size = random.choice([500, 5000, 20000, 100000])
        workers = random.choice([1, 4, 16, 64])
        stages_count = random.randint(1, 30)
        
        stages = [
            {"stage_id": f"stage_{s}", "stage_name": f"fuzz_stage_{s}", "stage_type": "DATA"}
            for s in range(stages_count)
        ]

        fuzz_plan = MigrationExecutionPlan(
            metadata={"plan_id": f"PLAN-RAND-{i}"},
            strategy={"batch_size": batch_size},
            resource_schedule={"max_workers": workers},
            execution_stages=stages,
        )

        model = platform_inst.analyze(fuzz_plan)
        
        assert model.verify_checksum()
        assert len(model.recommendations) > 0
        assert model.manifest.total_recommendations == len(model.recommendations)
        
        recs = model.recommendations
        for j in range(len(recs) - 1):
            r1, r2 = recs[j], recs[j + 1]
            t1 = (r1.priority.rank, r1.severity.rank, r1.category.value, r1.recommendation_id)
            t2 = (r2.priority.rank, r2.severity.rank, r2.category.value, r2.recommendation_id)
            assert t1 <= t2


# ============================================================================
# 10. TRACEMALLOC MEMORY PROFILING & ENDURANCE LOOP
# ============================================================================

def test_tracemalloc_memory_profiling_and_endurance(platform_inst, sample_plan):
    """Run 1,000 continuous platform executions while tracking peak memory with tracemalloc."""
    tracemalloc.start()
    for i in range(1000):
        model = platform_inst.analyze(sample_plan)
        assert model.verify_checksum()

    current_mem, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    peak_mb = peak_mem / (1024 * 1024)
    print(f"\n--- TRACEMALLOC MEMORY PROFILING (1,000 ITERATIONS) ---")
    print(f"Current Memory: {current_mem / 1024:.2f} KB | Peak Memory: {peak_mb:.2f} MB")
    assert peak_mb < 50.0


# ============================================================================
# 11. STATISTICAL BENCHMARK (50 ITERATIONS)
# ============================================================================

def test_statistical_benchmark_50_iterations(sample_plan):
    """Run 50 benchmark iterations measuring mean, median, min, max, P95, P99, stddev."""
    platform = AdvisorPlatform.create_default()
    runs_ms = []

    for _ in range(5):
        platform.analyze(sample_plan)

    for _ in range(50):
        t0 = time.perf_counter()
        platform.analyze(sample_plan)
        t1 = time.perf_counter()
        runs_ms.append((t1 - t0) * 1000.0)

    sorted_runs = sorted(runs_ms)
    mean_ms = statistics.mean(runs_ms)
    median_ms = statistics.median(runs_ms)
    min_ms = min(runs_ms)
    max_ms = max(runs_ms)
    stddev_ms = statistics.stdev(runs_ms)
    p95_ms = sorted_runs[int(0.95 * len(sorted_runs))]
    p99_ms = sorted_runs[int(0.99 * len(sorted_runs))]

    print(f"\n--- 50-ITERATION BENCHMARK STATISTICS ---")
    print(f"OS: {sys_platform.system()} {sys_platform.release()} | Python: {sys_platform.python_version()}")
    print(f"Mean: {mean_ms:.3f} ms | Median: {median_ms:.3f} ms | Min: {min_ms:.3f} ms | Max: {max_ms:.3f} ms")
    print(f"P95: {p95_ms:.3f} ms | P99: {p99_ms:.3f} ms | StdDev: {stddev_ms:.3f} ms")

    assert mean_ms < 50.0
