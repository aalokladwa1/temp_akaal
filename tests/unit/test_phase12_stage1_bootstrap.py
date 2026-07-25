"""
Unit tests for Phase 12 Stage 1: Platform Bootstrap & Composition Root.
"""

import pytest
from akaal.integration.composition_root import (
    EnterpriseLifecycleManager,
    RuntimeLifecycleState,
    CrossPlatformContext,
    execute_e2e_smoke_test,
)


def test_stage1_platform_bootstrap_success():
    manager = EnterpriseLifecycleManager()
    assert manager.current_state == RuntimeLifecycleState.CREATED

    context = manager.bootstrap()
    assert isinstance(context, CrossPlatformContext)
    assert manager.current_state == RuntimeLifecycleState.READY

    # Verify Platforms 1-9 facades
    assert context.workflow_engine is not None
    assert context.validation_platform is not None
    assert context.self_healing_platform is not None
    assert context.operations_platform is not None

    # Verify Pre-Phase 12 Core Engines
    assert context.resume_engine is not None
    assert context.deduplication_engine is not None
    assert context.expansion_engine is not None
    assert context.batch_validator is not None
    assert context.bottleneck_detector is not None
    assert context.throughput_optimizer is not None
    assert context.parallelism_engine is not None


def test_stage1_idempotent_bootstrap():
    manager = EnterpriseLifecycleManager()
    ctx1 = manager.bootstrap()
    assert manager.current_state == RuntimeLifecycleState.READY

    # Second bootstrap call without force_reset
    ctx2 = manager.bootstrap()
    assert ctx1 is ctx2
    assert manager.current_state == RuntimeLifecycleState.READY


def test_stage1_startup_diagnostics():
    manager = EnterpriseLifecycleManager()
    manager.bootstrap()
    diagnostics = manager.get_startup_diagnostics()

    assert diagnostics["system"] == "AKAAL Enterprise Migration Platform"
    assert diagnostics["runtime_state"] == "READY"
    assert diagnostics["health_summary"]["system_status"] == "HEALTHY"
    assert len(diagnostics["registrations"]["registered_platform_facades"]) == 9
    assert len(diagnostics["registrations"]["registered_core_engines"]) == 7
    assert len(diagnostics["registrations"]["registered_agents"]) == 11
    assert len(diagnostics["topological_startup_order"]) == 9


def test_stage1_lifecycle_running_and_shutdown():
    manager = EnterpriseLifecycleManager()
    manager.bootstrap()

    manager.mark_running()
    assert manager.current_state == RuntimeLifecycleState.RUNNING

    shutdown_ok = manager.shutdown()
    assert shutdown_ok is True
    assert manager.current_state == RuntimeLifecycleState.STOPPED


def test_stage1_e2e_smoke_test():
    manager = EnterpriseLifecycleManager()
    context = manager.bootstrap()
    results = execute_e2e_smoke_test(context)

    assert results["e2e_summary"]["status"] == "SUCCESS"
    assert results["pre_phase12_engines"]["status"] == "SUCCESS"
    assert results["pre_phase12_engines"]["deduplication_engine"] is True
