"""Tests for Diagnostics, Root Cause Analysis, Checkpoints, and Recovery Engines."""

import pytest
from akaal.reliability.diagnostics.root_cause import (
    DependencyHealthGraph,
    RootCauseAnalysisEngine,
    SelfDiagnosticsEngine,
    FailurePredictor,
)
from akaal.reliability.recovery.orchestrator import (
    CheckpointRecoveryEngine,
    DisasterRecoveryManager,
    ReliabilityRollbackEngine,
    StatefulRecoveryOrchestrator,
)
from akaal.reliability.core.context import ReliabilityContext


def test_dependency_graph_and_root_cause():
    graph = DependencyHealthGraph()
    graph.set_node_health("database_primary", 30.0)

    rc_engine = RootCauseAnalysisEngine(graph)
    res = rc_engine.analyze_root_cause("auth_service", "Upstream error")
    assert res["root_cause_type"] == "DEPENDENCY_FAILURE"
    assert res["failure_origin"] == "database_primary"


def test_self_diagnostics_and_predictor():
    sd = SelfDiagnosticsEngine()
    assert sd.run_self_diagnostics()["status"] == "PASS"

    fp = FailurePredictor()
    pred = fp.predict_failure_risk(health_score=60.0, consecutive_errors=2)
    assert pred["upcoming_failure_probability"] > 0.0


def test_checkpoint_and_rollback():
    chk_engine = CheckpointRecoveryEngine()
    chk_id = chk_engine.create_checkpoint("sess_001", {"offset": 5000})
    assert chk_id.startswith("chk_")

    rb_engine = ReliabilityRollbackEngine()
    rb_res = rb_engine.rollback_to_checkpoint("sess_001", chk_engine)
    assert rb_res["status"] == "ROLLBACK_SUCCESSFUL"
    assert rb_res["restored_state"]["offset"] == 5000


def test_disaster_recovery_manager():
    dm = DisasterRecoveryManager()
    ctx = ReliabilityContext()
    dr_res = dm.trigger_disaster_recovery("us-east", ctx)
    assert dr_res["status"] == "DISASTER_RECOVERY_COMPLETED"
