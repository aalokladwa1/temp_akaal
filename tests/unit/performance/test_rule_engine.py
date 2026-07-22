"""
Unit Tests for Decision Layer (Rule Engine, Policy Engine, Confidence scoring).
"""

from akaal.performance.decision.rule_engine import RuleEngine, OptimizationRule
from akaal.performance.decision.policy_engine import PolicyEngine, EnterprisePolicy
from akaal.performance.decision.confidence import ConfidenceEngine, ConfidenceCategory


def test_confidence_engine():
    # Calculate confidence score
    confidence = ConfidenceEngine.calculate(metric_delta=0.4, success_history=0.9, risk_factor=0.1)
    
    assert confidence.score > 80.0
    assert confidence.category == ConfidenceCategory.HIGH
    assert confidence.expected_improvement > 0.0


def test_rule_evaluation():
    rule_engine = RuleEngine()
    
    # Test metric trigger
    metrics = {"queue_depth": 150}
    recs = rule_engine.evaluate_metrics(metrics)
    
    assert len(recs) == 1
    assert recs[0].rule_id == "rule_high_queue"
    assert recs[0].params["worker_count"] == 8


def test_policy_engine_enforcement():
    policy = EnterprisePolicy(
        policy_id="test_pol",
        version="1.0",
        max_cpu_percent=80.0,
        max_workers=4
    )
    policy_engine = PolicyEngine(default_policy=policy)
    
    # Allowed
    assert policy_engine.is_permitted("parallelism", {"worker_count": 2}) is True
    # Violation of max_workers
    assert policy_engine.is_permitted("parallelism", {"worker_count": 8}) is False
    # Violation of max_cpu_percent
    assert policy_engine.is_permitted("batch_sizing", {"cpu_percent": 90.0}) is False
