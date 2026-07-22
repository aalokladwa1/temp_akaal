"""
Unit Tests for Security Engine, Governance Audit, and Recommendations.
"""

from akaal.operations.security.rbac import SecurityEngine, Role
from akaal.operations.governance.audit import GovernanceAuditCenter
from akaal.operations.recommendations.engine import OperationalRecommendationEngine


def test_security_rbac():
    sec = SecurityEngine()
    sec.assign_role("op1", Role.OPERATOR)
    sec.assign_role("auditor1", Role.AUDITOR)

    assert sec.is_authorized("op1", "control") is True
    assert sec.is_authorized("op1", "emergency_stop") is False
    assert sec.is_authorized("auditor1", "control") is False
    assert sec.is_authorized("auditor1", "audit_read") is True


def test_governance_audit_tamper_evidence():
    audit = GovernanceAuditCenter()
    rec1 = audit.record_action("op1", "DRAIN_WORKER", {"worker": "w1"})
    rec2 = audit.record_action("op1", "PAUSE_JOB", {"job": "j1"})

    assert audit.verify_chain_integrity() is True

    # Simulate tamper
    rec1.details["worker"] = "tampered_w2"
    assert audit.verify_chain_integrity() is False


def test_recommendation_engine_explainability():
    engine = OperationalRecommendationEngine()
    recs = engine.analyze_telemetry({"cpu_percent": 90.0}, health_score=65.0)

    assert len(recs) == 2
    assert recs[0].auto_executable is False  # Mandatory non-automation rule
    assert recs[0].confidence_score > 80.0
