"""Tests for Reliability Decision Engine decision paths."""

import pytest
from akaal.reliability.decision.engine import ReliabilityDecisionEngine
from akaal.reliability.decision.context import DecisionContext
from akaal.reliability.decision.evaluator import ReliabilityDecisionChoice


def test_decision_engine_choices():
    engine = ReliabilityDecisionEngine()

    # Healthy context -> RETRY
    ctx_normal = DecisionContext(health_score=95.0, failure_count=0)
    assert engine.make_decision(ctx_normal) == ReliabilityDecisionChoice.RETRY

    # Disaster state -> ABORT
    ctx_disaster = DecisionContext(current_state="Disaster", health_score=10.0)
    assert engine.make_decision(ctx_disaster) == ReliabilityDecisionChoice.ABORT

    # Circuit breaker open -> DEGRADE
    ctx_cb = DecisionContext(circuit_breaker_open=True, health_score=75.0)
    assert engine.make_decision(ctx_cb) == ReliabilityDecisionChoice.DEGRADE

    # Consecutive errors > 5 -> RESTART
    ctx_restart = DecisionContext(consecutive_errors=6, health_score=80.0)
    assert engine.make_decision(ctx_restart) == ReliabilityDecisionChoice.RESTART

    # Low health score -> RECOVER
    ctx_recover = DecisionContext(health_score=50.0)
    assert engine.make_decision(ctx_recover) == ReliabilityDecisionChoice.RECOVER
