"""
Comprehensive End-to-End Integration Suite for all 8 Pre-Phase 12 Engine Enhancements.
"""

import pytest
from akaal.orchestration.checkpoint.checkpoint import WorkflowCheckpoint
from akaal.orchestration.domain.identifiers import WorkflowId, JobId
from akaal.orchestration.domain.types import EngineState
from akaal.migration.execution.resume_engine import DeterministicResumeEngine
from akaal.data_integrity.batch_validator import BatchLevelValidator
from akaal.migration.execution.deduplication import ZeroDuplicateMigrationEngine
from akaal.operational_reliability.bottleneck_detector import MigrationBottleneckDetector
from akaal.performance.optimizers.throughput import AdaptiveThroughputOptimizer
from akaal.performance.optimizers.adaptive_parallelism import AdaptiveParallelismEngine
from akaal.migration.execution.expansion_engine import DatabaseExpansionEngine
from akaal.core.models.enums import SystemType


def test_e2e_pre_phase_12_pipeline_workflow():
    # 1. Database Expansion
    expansion_engine = DatabaseExpansionEngine(target_dialect=SystemType.POSTGRESQL)
    chunks = expansion_engine.compute_partition_chunks("orders", "id", 1, 2000, num_chunks=2)
    assert len(chunks) == 2
    bulk_sql = expansion_engine.generate_bulk_load_command("orders", "/tmp/orders.csv")
    assert "COPY orders FROM" in bulk_sql

    # 2. Zero-Duplicate Migration Engine
    dedup_engine = ZeroDuplicateMigrationEngine(target_dialect=SystemType.POSTGRESQL)
    raw_records = [
        {"id": 1, "amount": 100.0},
        {"id": 2, "amount": 200.0},
        {"id": 1, "amount": 100.0},  # Duplicate
    ]
    dedup_res = dedup_engine.process_batch("orders", raw_records, ["id", "amount"], ["id"])
    assert dedup_res.deduplicated_rows == 2
    assert dedup_res.duplicates_filtered == 1
    assert "ON CONFLICT (id) DO UPDATE" in dedup_res.upsert_sql

    # 3. Batch-Level Validation
    batch_validator = BatchLevelValidator()
    val_res = batch_validator.validate_batch(
        batch_index=1,
        table_name="orders",
        records=raw_records[:2],
        transaction_id="tx-e2e-100",
        uncommitted_count=0,
    )
    assert val_res.is_valid is True

    # 4. Smart Checkpoint Compression
    chk = WorkflowCheckpoint(
        checkpoint_id="chk-e2e-001",
        workflow_id=WorkflowId("wf-e2e"),
        job_id=JobId("job-e2e"),
        step_name="batch_sync",
        step_index=1,
        engine_state=EngineState.RUNNING,
        workflow_version="1.0.0",
        config_version=1,
        config_checksum="cfg-hash",
        state_data={"last_committed_batch": 1, "last_seen_pk": 2},
    )
    comp_dict = chk.serialize_compressed(codec="gzip")
    assert comp_dict["compressed"] is True

    restored_chk = WorkflowCheckpoint.from_dict(comp_dict)
    assert restored_chk.verify_checksum() is True
    assert restored_chk.state_data["last_seen_pk"] == 2

    # 5. Deterministic Resume Engine
    resume_engine = DeterministicResumeEngine()
    resume_spec = resume_engine.build_resume_spec("orders", restored_chk, pk_columns=["id"])
    assert resume_spec.resume_mode == "PRIMARY_KEY"
    assert resume_spec.where_clause == "orders.id > :last_seen_pk"

    # 6. Telemetry Monitoring & Bottleneck Detection
    telemetry = {
        "cpu_percent": 55.0,
        "memory_utilization_pct": 60.0,
        "lock_wait_time_ms": 120.0,  # Lock bottleneck
        "queue_depth": 150,
        "active_workers": 2,
    }
    detector = MigrationBottleneckDetector()
    report = detector.analyze_runtime_telemetry(telemetry)
    assert len(report.bottlenecks) >= 1
    assert report.bottlenecks[0].category == "LOCK_CONTENTION"

    # 7. Adaptive Throughput Optimization
    throughput_optimizer = AdaptiveThroughputOptimizer()
    t_spec = throughput_optimizer.optimize_throughput(telemetry, {"batch_size": 500})
    assert t_spec.batch_size > 0

    # 8. Adaptive Parallelism Engine
    parallel_engine = AdaptiveParallelismEngine()
    p_decision = parallel_engine.autoscale_workers(telemetry, current_workers=2)
    assert p_decision.recommended_workers >= 1
