"""Tests for Subsystems 1, 2, and 3: Decision Engine, Topology Graph, and Sandbox Simulation."""

import pytest
from akaal.replication.decision.engine import ReplicationDecisionEngine
from akaal.replication.decision.evaluator import ReplicationDecisionChoice
from akaal.replication.decision.context import DecisionContext
from akaal.replication.topology.graph import ReplicationTopologyGraph
from akaal.replication.topology.analyzer import TopologyAnalyzer, TopologyPlanner, RouteOptimizer
from akaal.replication.topology.discovery import TopologyDiscoveryManager
from akaal.replication.core.models import ReplicaNode, ReplicaRole, ReplicationPlan, ReplicationAction
from akaal.replication.sandbox.sandbox import ReplicationSandbox


def test_decision_engine_choices():
    engine = ReplicationDecisionEngine()

    # Normal healthy context -> REPLICATE
    ctx_normal = DecisionContext(replica_health_score=95.0, replication_lag_ms=10.0)
    assert engine.make_decision(ctx_normal) == ReplicationDecisionChoice.REPLICATE

    # Unhealthy cluster -> FAILOVER
    ctx_failover = DecisionContext(cluster_health="UNHEALTHY", replica_health_score=30.0)
    assert engine.make_decision(ctx_failover) == ReplicationDecisionChoice.FAILOVER

    # High lag -> RETRY
    ctx_retry = DecisionContext(replication_lag_ms=6000.0, sla_max_lag_ms=5000.0)
    assert engine.make_decision(ctx_retry) == ReplicationDecisionChoice.RETRY

    # High risk under STRICT_FINANCE -> PAUSE
    ctx_pause = DecisionContext(replica_health_score=70.0, network_status="DEGRADED", policy_profile="STRICT_FINANCE", business_criticality="CRITICAL", error_count=5)
    assert engine.make_decision(ctx_pause) == ReplicationDecisionChoice.PAUSE


def test_topology_graph_and_analyzer():
    discovery = TopologyDiscoveryManager()
    graph = discovery.discover_live_topology(["us-east", "eu-central"])

    assert len(graph.nodes) >= 4
    assert graph.detect_circular_routes() is False

    analyzer = TopologyAnalyzer()
    report = analyzer.analyze_topology(graph)
    assert report["healthy"] is True
    assert report["is_multi_region"] is True


def test_topology_failover_planner_and_route_optimizer():
    graph = ReplicationTopologyGraph()
    n_prim = ReplicaNode(node_id="p1", region="us-east", role=ReplicaRole.PRIMARY, is_active=True)
    n_sec1 = ReplicaNode(node_id="s1", region="us-east", role=ReplicaRole.SECONDARY, is_active=True, health_score=95.0, lag_ms=5.0)
    n_sec2 = ReplicaNode(node_id="s2", region="us-east", role=ReplicaRole.SECONDARY, is_active=True, health_score=99.0, lag_ms=2.0)

    graph.add_node(n_prim)
    graph.add_node(n_sec1)
    graph.add_node(n_sec2)
    graph.add_replication_path("p1", "s1")
    graph.add_replication_path("p1", "s2")

    planner = TopologyPlanner()
    promoted = planner.plan_failover(graph, "p1")
    assert promoted == "s2"

    optimizer = RouteOptimizer()
    path = optimizer.find_optimal_route(graph, "p1", "s2")
    assert path == ["p1", "s2"]


def test_replication_sandbox_dry_run():
    sandbox = ReplicationSandbox()
    plan = ReplicationPlan(
        actions=[
            ReplicationAction(source_node_id="node_a", target_node_id="node_b", row_count=500),
            ReplicationAction(source_node_id="node_b", target_node_id="node_c", row_count=1500),
        ]
    )

    report = sandbox.run_dry_run(plan)
    assert report.is_safe is True
    assert report.predicted_duration_ms > 0
    assert report.rollback_probability < 0.10
    assert "node_a" in report.affected_nodes
