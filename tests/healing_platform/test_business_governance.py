"""Tests for BusinessImpactAnalyzer, PolicyEngine, and AuditTrail."""

import pytest
from akaal.healing.business.analyzer import BusinessImpactAnalyzer
from akaal.healing.business.criticality import RiskLevel
from akaal.healing.policy.engine import HealingPolicyEngine
from akaal.healing.core.config import HealingProfile, ApprovalMode
from akaal.healing.services.audit import RepairAuditTrailService


def test_business_impact_analyzer():
    analyzer = BusinessImpactAnalyzer()
    report_orders = analyzer.analyze("orders")
    assert report_orders.risk_level == RiskLevel.CRITICAL
    assert report_orders.requires_executive_approval is True

    report_logs = analyzer.analyze("system_logs")
    assert report_logs.risk_level == RiskLevel.MEDIUM
    assert report_logs.requires_executive_approval is False


def test_healing_policy_engine():
    engine_fin = HealingPolicyEngine(profile=HealingProfile.STRICT_FINANCE)
    res_fin = engine_fin.evaluate_repair(None)
    assert res_fin["requires_approval"] is True
    assert res_fin["approval_level"] == "EXECUTIVE"

    engine_auto = HealingPolicyEngine(profile=HealingProfile.AUTOMATIC, approval_mode=ApprovalMode.AUTOMATIC)
    res_auto = engine_auto.evaluate_repair(None)
    assert res_auto["requires_approval"] is False


def test_audit_trail_service():
    audit = RepairAuditTrailService()
    audit.log_repair_entry("session_101", "RESTORE_ROW", "COMPLETED")
    trail = audit.get_audit_trail("session_101")
    assert len(trail) == 1
    assert trail[0]["action_name"] == "RESTORE_ROW"
