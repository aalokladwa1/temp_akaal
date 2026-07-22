"""
Integration Test Suite for AKAAL Enterprise Platform Composition Root.
Verifies registration, dependency resolution, startup, health aggregation,
capability discovery, end-to-end smoke test, and graceful shutdown across all 9 platforms.
"""

import pytest
from akaal.integration import (
    EnterpriseLifecycleManager,
    PlatformRegistry,
    PlatformDescriptor,
    DependencyGraph,
    HealthRegistry,
    CrossPlatformContext,
    execute_e2e_smoke_test,
    DuplicatePlatformError,
    MissingPlatformError,
    PlatformValidationFailedError,
    CircularDependencyError,
)


def test_enterprise_composition_bootstrap_and_smoke_test():
    """Verify that all 9 platforms bootstrap cleanly and execute an end-to-end smoke test."""
    manager = EnterpriseLifecycleManager()
    context = manager.bootstrap()

    assert context is not None
    assert len(context.list_platforms()) == 9

    # Verify health aggregation
    health = context.get_health()
    assert health["system_status"] == "HEALTHY"
    assert health["platform_count"] == 9
    assert health["healthy_count"] == 9

    # Execute end-to-end smoke test
    smoke = execute_e2e_smoke_test(context)
    assert smoke["e2e_summary"]["status"] == "SUCCESS"
    assert smoke["e2e_summary"]["platforms_verified"] == 8

    # Verify shutdown
    assert manager.shutdown() is True


def test_platform_registry_duplicate_and_missing_errors():
    """Verify that duplicate platform registration fails and missing queries raise errors."""
    registry = PlatformRegistry()
    desc = PlatformDescriptor("platform-1", "Mock Workflow", None, "1.0.0")

    registry.register(desc)
    assert registry.get_platform("platform-1").name == "Mock Workflow"

    with pytest.raises(DuplicatePlatformError):
        registry.register(desc)

    with pytest.raises(MissingPlatformError):
        registry.get_platform("non-existent-platform")


def test_dependency_graph_topological_order_and_cycle_detection():
    """Verify topological ordering and circular dependency detection."""
    registry = PlatformRegistry()
    registry.register(PlatformDescriptor("platform-A", "A", None, "1.0", dependencies=["platform-B"]))
    registry.register(PlatformDescriptor("platform-B", "B", None, "1.0", dependencies=[]))

    graph = DependencyGraph(registry)
    assert graph.detect_circular_dependencies() is False
    order = graph.get_startup_order()
    assert order == ["platform-B", "platform-A"]

    # Introduce cycle
    registry_cycle = PlatformRegistry()
    registry_cycle.register(PlatformDescriptor("platform-X", "X", None, "1.0", dependencies=["platform-Y"]))
    registry_cycle.register(PlatformDescriptor("platform-Y", "Y", None, "1.0", dependencies=["platform-X"]))
    graph_cycle = DependencyGraph(registry_cycle)
    assert graph_cycle.detect_circular_dependencies() is True

    with pytest.raises(CircularDependencyError):
        graph_cycle.get_startup_order()


def test_capability_discovery_and_versions():
    """Verify read-only capability and version retrieval across all 9 platforms."""
    manager = EnterpriseLifecycleManager()
    context = manager.bootstrap()

    versions = context.get_versions()
    assert len(versions) == 9
    assert all(v == "1.0.0" for v in versions.values())

    caps = context.get_capabilities()
    assert len(caps) == 9
    assert "platform-1" in caps
    assert "platform-7" in caps
    assert "features" in caps["platform-7"]

    manager.shutdown()
