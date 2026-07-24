"""Tests for DecisionEngine, RepairDependencyGraph, and RepairSandbox."""

import pytest
from akaal.healing.decision.engine import DecisionEngine
from akaal.healing.decision.context import DecisionContext
from akaal.healing.decision.evaluator import RepairDecisionChoice
from akaal.healing.dependency.graph import RepairDependencyGraph
from akaal.healing.sandbox.sandbox import RepairSandbox
from akaal.healing.core.models import HealingPlan, HealingStep, RepairAction


def test_decision_engine():
    engine = DecisionEngine()
    ctx = DecisionContext(issue_severity="ERROR", confidence_score=95.0)
    choice = engine.make_decision(ctx)
    assert choice in (RepairDecisionChoice.REPAIR, RepairDecisionChoice.RETRY, RepairDecisionChoice.ROLLBACK, RepairDecisionChoice.ESCALATE)


def test_repair_dependency_graph():
    graph = RepairDependencyGraph()
    graph.add_dependency("users", "orders")
    graph.add_dependency("orders", "payments")

    assert graph.detect_cycles() is False
    order = graph.get_topological_order()
    assert order == ["users", "orders", "payments"]


def test_repair_sandbox_dry_run():
    sandbox = RepairSandbox()
    plan = HealingPlan(
        session_id="s123",
        steps=[HealingStep(step_id="step1", name="restore_users", actions=[RepairAction(target_table="users")])],
    )
    report = sandbox.run_dry_run(plan)
    assert report is not None
    assert report.is_safe is True
    assert "users" in report.affected_tables
