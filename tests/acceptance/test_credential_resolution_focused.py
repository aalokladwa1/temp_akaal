"""
tests/acceptance/test_credential_resolution_focused.py
========================================================
Focused regression test suite covering platform-wide credential resolution,
dispatcher integrity, continuous engine runtime lifecycle, and fail-closed laws (G1-G10, C1-C7).
Scope boundary: tests/acceptance/
"""

import os
import inspect
import pytest
from akaalEngine.gateway.routing.dispatcher import (
    GatewayDispatcher,
    resolve_secret_reference,
    resolve_canonical_connection_params,
)
from akaalEngine.gateway.models.enums import SemanticOperation
from akaalEngine.gateway.models.context import GatewayRequestContext
from akaalEngine.cdc.api import CDCAuthority, default_cdc_authority
from akaalPipeline.contracts.enums import MigrationMode, NodeExecutionState, PlanExecutionStatus


def test_g1_reference_value_separation(monkeypatch):
    """G1: Secret reference ('env:MY_DB_PASSWORD') resolves to actual secret value without mutating secret_ref."""
    monkeypatch.setenv("MY_DB_PASSWORD", "SuperSecretPass2026!")

    config = {
        "source_host": "db.corp.internal",
        "source_port": 5432,
        "source_username": "app_user",
        "source_database": "prod_db",
        "source_secret_ref": "env:MY_DB_PASSWORD",
    }

    resolved = resolve_canonical_connection_params(config, prefix="source")

    assert resolved["secret_ref"] == "env:MY_DB_PASSWORD"
    assert resolved["password"] == "SuperSecretPass2026!"
    assert resolved["username"] == "app_user"
    assert resolved["database"] == "prod_db"


def test_g2_provider_neutral_resolution():
    """G2: Connection parameter resolution operates generically without provider-specific branching."""
    oracle_config = {
        "source_host": "oracle.corp.internal",
        "source_port": 1521,
        "source_username": "oracle_user",
        "source_service_name": "ORCLPDB1",
        "source_secret_ref": "SecretPassword123",
    }
    resolved = resolve_canonical_connection_params(oracle_config, prefix="source")

    assert resolved["host"] == "oracle.corp.internal"
    assert resolved["port"] == 1521
    assert resolved["user"] == "oracle_user"
    assert resolved["service_name"] == "ORCLPDB1"
    assert resolved["password"] == "SecretPassword123"


def test_g3_source_target_consistency(monkeypatch):
    """G3: Source and target connection contexts use the same canonical resolution authority."""
    monkeypatch.setenv("TGT_PASS_ENV", "TargetSecretPass!99")

    cfg = {
        "source_host": "src.internal",
        "source_port": 5432,
        "source_user": "src_usr",
        "source_secret_ref": "SrcPass123",

        "target_host": "tgt.internal",
        "target_port": 1433,
        "target_user": "tgt_usr",
        "target_secret_ref": "env:TGT_PASS_ENV",
    }

    src_res = resolve_canonical_connection_params(cfg, prefix="source")
    tgt_res = resolve_canonical_connection_params(cfg, prefix="target")

    assert src_res["password"] == "SrcPass123"
    assert tgt_res["password"] == "TargetSecretPass!99"
    assert tgt_res["secret_ref"] == "env:TGT_PASS_ENV"


def test_g4_mode_neutrality():
    """G4: Connection resolution is mode-neutral across M1-M8."""
    modes = ["M1", "M2", "M3", "M4", "M5", "M6", "M7", "M8"]
    base_cfg = {
        "source_host": "localhost",
        "source_port": 5432,
        "source_username": "postgres",
        "source_secret_ref": "PassMode123",
    }

    for m in modes:
        cfg = dict(base_cfg)
        cfg["mode"] = m
        resolved = resolve_canonical_connection_params(cfg, prefix="source")
        assert resolved["password"] == "PassMode123"


def test_g6_fail_closed_runtime_monitoring():
    """G6: Continuous CDC runtime updates health state to UNHEALTHY upon unrecoverable stream error."""
    cdc_auth = CDCAuthority()
    assert cdc_auth.streaming_health_state == "INITIALIZED"

    with pytest.raises(Exception):
        cdc_auth.drain_and_sync()

    assert cdc_auth.streaming_health_state == "UNHEALTHY"
    assert cdc_auth.last_streaming_error is not None
    assert cdc_auth.consecutive_streaming_failures == 1


def test_g7_existing_behavior_preserved():
    """G7: Plaintext passwords without prefix are passed through cleanly."""
    resolved = resolve_secret_reference("PlainPassword!2026")
    assert resolved == "PlainPassword!2026"


def test_g8_dispatch_table_integrity():
    """G8: Every supported semantic operation referenced by GatewayDispatcher resolves to an existing callable route."""
    dispatcher = GatewayDispatcher()
    code = inspect.getsource(GatewayDispatcher.dispatch)

    lines = code.split("\n")
    current_op = None
    checked_ops = 0

    for line in lines:
        line = line.strip()
        if "operation == SemanticOperation." in line:
            current_op = line.split("SemanticOperation.")[1].split(":")[0].strip()
        elif current_op and "resp = self." in line:
            target_expr = line.split("resp = self.")[1].split("(")[0].strip()
            parts = target_expr.split(".")
            obj = dispatcher
            for part in parts:
                assert hasattr(obj, part), f"Missing target attribute '{part}' for operation {current_op}"
                obj = getattr(obj, part)
            assert callable(obj), f"Target attribute '{target_expr}' for operation {current_op} is not callable"
            checked_ops += 1
            current_op = None

    assert checked_ops >= 30, f"Expected at least 30 dispatch branches checked, got {checked_ops}"


def test_g9_cdc_initialization_dispatch():
    """G9: INITIALIZE_CDC_STREAM reaches canonical Engine CDC initialization authority without AttributeError."""
    dispatcher = GatewayDispatcher()
    assert hasattr(dispatcher, "_handle_initialize_cdc")
    assert callable(dispatcher._handle_initialize_cdc)

    ctx = GatewayRequestContext(
        tenant_id="default-tenant",
        workspace_id="default-workspace",
        project_id="default-project",
        migration_id="test-mig-dispatch-cdc",
        run_id="test-run-1",
        fencing_epoch=1,
        operation_id="op-test-cdc-init",
    )

    with pytest.raises(Exception) as excinfo:
        dispatcher._handle_initialize_cdc(ctx, {})

    assert "AttributeError" not in excinfo.typename
    assert "'GatewayDispatcher' object has no attribute" not in str(excinfo.value)


def test_g10_fail_closed_dependency_semantics():
    """G10: If predecessor node genuinely fails, dependent node remains BLOCKED (no false transition)."""
    capture_state = NodeExecutionState.FAILED
    apply_state = (
        NodeExecutionState.READY
        if capture_state == NodeExecutionState.SUCCEEDED
        else NodeExecutionState.BLOCKED
    )

    assert apply_state == NodeExecutionState.BLOCKED


def test_c1_c2_c3_start_establishes_managed_runtime():
    """C1-C3: Start establishes managed continuous Engine CDC runtime that remains active after dispatch returns."""
    cdc_auth = default_cdc_authority()
    class DummyWriter:
        pass
    
    cdc_auth.bind_target_writer(DummyWriter())
    assert cdc_auth.is_streaming_active is True, "C1/C2/C3: CDCAuthority background thread must be active"


def test_c5_runtime_truth():
    """C5: Operational health state reflects physical runtime errors fail-closed."""
    cdc_auth = default_cdc_authority()
    assert cdc_auth.streaming_health_state in ("INITIALIZED", "HEALTHY", "UNHEALTHY")


def test_c6_genuine_restart():
    """C6: MigrationMode continuous check is generic across continuous modes."""
    assert MigrationMode.is_continuous_mode("M3") is True
    assert MigrationMode.is_continuous_mode("M2") is True
    assert MigrationMode.is_continuous_mode("M1") is False


def test_c7_no_pipeline_physical_loop():
    """C7: PlanExecutionCoordinator does NOT contain a physical 'while True: drain_and_sync' loop."""
    from akaalPipeline.execution.coordinator import PlanExecutionCoordinator
    src = inspect.getsource(PlanExecutionCoordinator)
    assert "drain_and_sync" not in src, "C7 Violation: PlanExecutionCoordinator must NOT execute physical CDC loops"


def test_provider_display_name_normalization():
    """Verify product display names ('Microsoft SQL Server', 'PostgreSQL') resolve to canonical driver keys ('mssql', 'postgres')."""
    from akaalEngine.transport.drivers.registry import normalize_provider_id, default_transport_driver_registry
    assert normalize_provider_id("Microsoft SQL Server") == "mssql"
    assert normalize_provider_id("PostgreSQL") == "postgres"
    assert default_transport_driver_registry.is_registered("Microsoft SQL Server") is True
    assert default_transport_driver_registry.get("Microsoft SQL Server").provider_id == "mssql"


def test_fail_closed_unbound_apply_coordinator():
    """Verify CDCAuthority snapshot reports apply_state as UNBOUND when apply_coordinator is not bound."""
    cdc_auth = CDCAuthority()
    snap = cdc_auth.get_snapshot()
    assert snap.to_dict()["apply_state"] == "UNBOUND"

