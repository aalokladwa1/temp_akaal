"""
tests/integration/engine_cdc/test_cdc_integration.py
======================================================
Integration tests for Authority #10 CDC physical integration with Authorities #1, #5, #6, #7, #8, #9.
"""

import tempfile
import pytest
from akaalEngine.cdc import (
    CDCApplyCoordinator,
    CDCAuthority,
    ChangeEvent,
    ChangeOperation,
    DeletionType,
    PostgresLSNPosition,
    TechnicalCutoverReadinessFacts,
)
from akaalEngine.data_processing import DataProcessingAuthority
from akaalEngine.durability import DurabilityAuthority, DurabilityConfig
from akaalEngine.runtime import RuntimeAuthority
from akaalEngine.telemetry import TelemetryAuthority
from akaalEngine.transport import FileTargetWriter, TransportAuthority


@pytest.fixture
def temp_durability_authority():
    with tempfile.TemporaryDirectory() as tmp_dir:
        config = DurabilityConfig(
            storage_dir=tmp_dir,
            fencing_signing_key=b"fencing_secret_key_1234567890123",
            journal_anchor_key=b"journal_anchor_key_1234567890123",
        )
        dur = DurabilityAuthority(config)
        yield dur
        dur.close()


def test_cdc_authority_full_integration(temp_durability_authority):
    """Proves CDCAuthority integrates cleanly with Data Processing, Transport, Telemetry, Runtime, and Durability."""
    dur = temp_durability_authority
    runtime = RuntimeAuthority(durability_authority=dur)
    runtime.start()

    telemetry = TelemetryAuthority(runtime_authority=runtime)
    data_processing = DataProcessingAuthority(telemetry_authority=telemetry, runtime_authority=runtime)
    transport = TransportAuthority(
        durability_authority=dur,
        runtime_authority=runtime,
        telemetry_authority=telemetry,
        data_processing_authority=data_processing,
    )

    cdc = CDCAuthority(
        durability_authority=dur,
        runtime_authority=runtime,
        telemetry_authority=telemetry,
        data_processing_authority=data_processing,
        transport_authority=transport,
    )

    with tempfile.NamedTemporaryFile("w+", delete=False, suffix=".csv") as f_tgt:
        writer = FileTargetWriter(f_tgt.name, "CSV")
        apply_coord = CDCApplyCoordinator(target_writer=writer, data_processing_authority=data_processing)

        event = ChangeEvent(
            event_id="evt-1001",
            source_system="POSTGRESQL",
            source_identity="db_prod",
            logical_object="customers",
            operation=ChangeOperation.INSERT,
            source_position="0/16B3748",
            commit_position="0/16B3748",
            commit_timestamp=1700000000.0,
            capture_timestamp=1700000001.0,
            schema_version="v1",
            key_columns=("id",),
            key_values={"id": 101},
            after_image={"id": 101, "name": "Alice", "status": "ACTIVE"},
        )

        applied = apply_coord.apply_event(event, table_name="customers")
        assert applied is True
        writer.close()

    # Test Cutover Readiness Facts & Telemetry Snapshot
    facts = TechnicalCutoverReadinessFacts(
        snapshot_complete=True,
        replication_lag_seconds=0.1,
        cdc_backlog_events=0,
        unresolved_transactions=0,
        ambiguous_commit_count=0,
        checkpoint_identity_valid=True,
        source_position_barrier_reached=True,
        target_applied_barrier_reached=True,
    )
    cdc.declare_technical_cutover_ready(facts)

    snap = cdc.get_snapshot()
    assert snap.cutover_state == "TECHNICAL_CUTOVER_READY"
    assert snap.technical_cutover_ready is True

    runtime.shutdown()
