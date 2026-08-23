"""
tests/unit/engine_cdc/test_handshake_cutover_and_backlog.py
===========================================================
Unit tests for SnapshotCDCHandshakeEngine, Cutover FSM, TechnicalCutoverReadinessGate, Synchronization Barriers, and Retention Protection.
"""

import pytest

from akaalEngine.cdc import (
    CDCAuthority,
    CDCBacklogBuffer,
    CDCCutoverNotReadyError,
    CutoverCoordinator,
    CutoverState,
    HandshakeMode,
    PostgresLSNPosition,
    RetentionState,
    SnapshotCDCHandshakeEngine,
    SourceRetentionMonitor,
    SynchronizationBarrierEngine,
    SynchronizationBarrierStrategy,
    TechnicalCutoverReadinessFacts,
    TechnicalCutoverReadinessGate,
)


def test_snapshot_cdc_handshake_boundary():
    """Proves SnapshotCDCHandshakeEngine establishes consistent start position P0."""
    engine = SnapshotCDCHandshakeEngine(HandshakeMode.CONSISTENT_SNAPSHOT_WITH_LOG_POSITION)
    lsn = PostgresLSNPosition("0/16B3748")

    pos, requires_quiesce = engine.establish_handshake_boundary(lsn)
    assert pos == lsn
    assert requires_quiesce is False


def test_cutover_fsm_transitions():
    """Proves CutoverCoordinator manages FSM state transitions."""
    coord = CutoverCoordinator()
    assert coord.state == CutoverState.SNAPSHOT_PREPARING

    coord.transition_to(CutoverState.SNAPSHOT_RUNNING)
    assert coord.state == CutoverState.SNAPSHOT_RUNNING


def test_technical_cutover_readiness_gate():
    """Proves TechnicalCutoverReadinessGate permits cutover only when ALL facts are proven."""
    facts_valid = TechnicalCutoverReadinessFacts(
        snapshot_complete=True,
        replication_lag_seconds=0.5,
        cdc_backlog_events=0,
        unresolved_transactions=0,
        ambiguous_commit_count=0,
        checkpoint_identity_valid=True,
        source_position_barrier_reached=True,
        target_applied_barrier_reached=True,
    )
    assert TechnicalCutoverReadinessGate.evaluate_readiness(facts_valid) is True

    facts_lagging = TechnicalCutoverReadinessFacts(
        snapshot_complete=True,
        replication_lag_seconds=15.0,  # Lagging > 2.0s
        cdc_backlog_events=100,
        unresolved_transactions=0,
        ambiguous_commit_count=0,
        checkpoint_identity_valid=True,
        source_position_barrier_reached=True,
        target_applied_barrier_reached=True,
    )
    assert TechnicalCutoverReadinessGate.evaluate_readiness(facts_lagging) is False


def test_synchronization_barrier_engine():
    """Proves SynchronizationBarrierEngine verifies target applied position against source barrier."""
    barrier = SynchronizationBarrierEngine(SynchronizationBarrierStrategy.LOG_MARKER_INJECTION)
    pos1 = PostgresLSNPosition("0/16B3748")
    pos2 = PostgresLSNPosition("0/16B3749")

    assert barrier.execute_barrier(pos2, pos1) is False
    assert barrier.execute_barrier(pos1, pos2) is True
    assert barrier.barrier_reached is True


def test_clamped_backlog_storage_calculation():
    """Proves CDCAuthority.calculate_backlog_storage_bytes clamps negative rate differences to 0."""
    cdc = CDCAuthority()

    # Apply rate > Source rate -> 0 bytes backlog
    assert cdc.calculate_backlog_storage_bytes(source_gen_rate=100.0, apply_rate=150.0, duration_sec=60.0) == 0.0

    # Source rate > Apply rate -> Positive backlog bytes with safety margin
    assert cdc.calculate_backlog_storage_bytes(source_gen_rate=200.0, apply_rate=100.0, duration_sec=60.0) == 7500.0


def test_source_retention_monitor():
    """Proves SourceRetentionMonitor emits warning and critical retention risk states."""
    monitor = SourceRetentionMonitor(warning_threshold_percent=15.0)

    # 50% free -> HEALTHY
    assert monitor.evaluate_retention("POSTGRESQL", total_capacity_bytes=1000, used_bytes=500) == RetentionState.HEALTHY

    # 10% free -> WARNING
    assert monitor.evaluate_retention("POSTGRESQL", total_capacity_bytes=1000, used_bytes=900) == RetentionState.WARNING

    # 2% free -> CRITICAL
    assert monitor.evaluate_retention("POSTGRESQL", total_capacity_bytes=1000, used_bytes=980) == RetentionState.CRITICAL
