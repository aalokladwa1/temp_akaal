"""
Unit Tests for Digital Twin, Topology Engine, and Capability Registry.
"""

from akaal.operations.digital_twin.model import DigitalTwinModel, ClusterNodeModel, WorkerModel
from akaal.operations.topology.engine import TopologyEngine
from akaal.operations.capability_registry.registry import OperationsCapabilityRegistry, PlatformCapability


def test_digital_twin_state_updates():
    twin = DigitalTwinModel()
    
    node = ClusterNodeModel("node1", "10.0.0.1")
    twin.update_node(node)
    assert "node1" in twin.nodes

    worker = WorkerModel("w1", "node1")
    twin.update_worker(worker)
    assert "w1" in twin.workers

    twin.update_health("Platform1", 80.0)
    assert twin.platform_health["Platform1"] == 80.0

    snapshot = twin.get_snapshot()
    assert snapshot["nodes"]["node1"] == "ACTIVE"


def test_topology_engine_relationships():
    topology = TopologyEngine()
    
    topology.add_node("cluster1", "Cluster", "Primary Cluster")
    topology.add_node("worker1", "Worker", "Worker Node 1")
    topology.add_relationship("cluster1", "worker1")

    children = topology.get_children("cluster1")
    assert len(children) == 1
    assert children[0].node_id == "worker1"


def test_capability_registry():
    registry = OperationsCapabilityRegistry()
    
    cap = PlatformCapability("Platform6", "1.0", ["set_profile", "trigger_optimization"])
    registry.register_capability(cap)

    assert registry.supports_action("Platform6", "set_profile") is True
    assert registry.supports_action("Platform6", "drain_worker") is False
