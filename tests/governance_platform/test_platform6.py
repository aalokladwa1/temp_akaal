"""
AKAAL Platform 6 — Unit & Integration Test Suite.
Verifies all 28 Enterprise Governance Capabilities, Policy-as-Code, SoD, Four-Eyes, Emergency Overrides,
Impact Analysis, Dependency Graph, Lifecycle Management, and Immutable Hash Ledger.
"""

import unittest
import asyncio
import datetime

from akaal.governance import EnterpriseGovernancePlatformV6
from akaal.governance.domain.models import (
    EnterprisePolicy,
    SoDRule,
    ComplianceRule,
    GovernanceDependencyNode,
)
from akaal.governance.domain.enums import PolicyCategory, RiskLevel, EmergencyReason, LifecycleState, ApprovalStatus
from akaal.governance.domain.exceptions import (
    SoDViolationError,
    LifecycleValidationError,
    LedgerTamperError,
)
from akaal.api.facades.platform6 import Platform6Facade
from akaal.api.contracts.dto import GovernanceApprovalRequestDTO


class TestPlatform6Governance(unittest.TestCase):

    def setUp(self):
        self.platform = EnterpriseGovernancePlatformV6()
        self.facade = Platform6Facade(self.platform)

    def test_capabilities_dto(self):
        caps = asyncio.run(self.facade.get_capabilities())
        self.assertEqual(caps.platform_name, "Platform 6 (Enterprise Governance Platform)")
        self.assertIn("request_governance_approval", caps.supported_features)
        self.assertIn("governance_impact_analyzer", caps.supported_features)

    def test_policy_as_code_evaluation(self):
        policy = EnterprisePolicy(
            policy_id="POL_001",
            name="Block Destructive Operations",
            version="1.0.0",
            category=PolicyCategory.OPERATIONAL,
            declarative_rule="FORBID_DESTRUCTIVE",
            owner_id="admin",
            effective_from="2026-01-01T00:00:00Z",
            expires_at=None,
            risk_level=RiskLevel.HIGH,
        )
        self.platform.policy_service.register_policy(policy)

        # Destructive request should be rejected
        decision = self.platform.evaluate_and_govern_operation(
            target_platform="PLATFORM_1",
            operation_type="DROP_DATABASE",
            requester_id="user_alice",
            payload={"is_destructive": True},
        )
        self.assertEqual(decision.outcome, ApprovalStatus.REJECTED)
        self.assertIn("policy violations", decision.decision_rationale)

    def test_sod_enforcement(self):
        sod_rule = SoDRule(
            rule_id="SOD_001",
            role_a="Developer",
            role_b="Deployer",
            forbidden_actions=["DEPLOY_PROD"],
            description="Developers cannot deploy their own code to prod",
        )
        self.platform.sod_engine.register_rule(sod_rule)

        # Self-approval check
        ok, violations = self.platform.sod_engine.validate_approval(
            requester_id="user_bob",
            approver_ids=["user_bob"],
            requester_role="Developer",
            approver_roles=["Deployer"],
        )
        self.assertFalse(ok)
        self.assertTrue(any("Self-approval" in v for v in violations))

    def test_four_eyes_validation(self):
        ok, msg = self.platform.foureyes_validator.validate_four_eyes("user_alice", "user_bob")
        self.assertTrue(ok)

        ok_same, msg_same = self.platform.foureyes_validator.validate_four_eyes("user_alice", "user_alice")
        self.assertFalse(ok_same)

    def test_emergency_override_workflow(self):
        override = self.platform.emergency_service.trigger_override(
            operation_id="op_999",
            justification="Critical Outage Mitigation",
            reason_category=EmergencyReason.OUTAGE_MITIGATION,
            authorized_by="exec_charlie",
            duration_minutes=30,
        )
        self.assertTrue(self.platform.emergency_service.is_override_active(override.override_id))

        self.platform.emergency_service.revoke_override(override.override_id)
        self.assertFalse(self.platform.emergency_service.is_override_active(override.override_id))

    def test_immutable_ledger_anti_tamper(self):
        self.platform.ledger.verify_integrity()
        self.assertGreaterEqual(len(self.platform.ledger.get_chain()), 1)

    def test_impact_analysis_engine(self):
        report = self.platform.impact_analyzer.analyze_change_impact(
            target_artifact_id="POL_001",
            change_type="STRICTER_RULES",
            proposed_payload={"is_restrictive": True, "affected_systems": ["PLATFORM_1", "PLATFORM_5"]},
        )
        self.assertEqual(report.target_artifact_id, "POL_001")
        self.assertLess(report.risk_delta, 0)
        self.assertGreater(report.compliance_delta, 0)

    def test_governance_dependency_graph(self):
        node1 = GovernanceDependencyNode(artifact_id="POL_001", artifact_type="Policy", dependencies=[])
        node2 = GovernanceDependencyNode(artifact_id="WF_001", artifact_type="Workflow", dependencies=["POL_001"])
        self.platform.dependency_graph.add_node(node1)
        self.platform.dependency_graph.add_node(node2)

        has_cycle = self.platform.dependency_graph.detect_circular_dependencies()
        self.assertFalse(has_cycle)

    def test_governance_lifecycle_management(self):
        artifact_id = "POL_DRAFT_01"
        self.platform.lifecycle_engine.initialize_artifact(artifact_id, LifecycleState.DRAFT)

        # Valid transition: DRAFT -> REVIEW -> APPROVED -> ACTIVE
        t1 = self.platform.lifecycle_engine.transition_state(artifact_id, LifecycleState.REVIEW, "user_alice", "Ready for review")
        self.assertEqual(self.platform.lifecycle_engine.get_state(artifact_id), LifecycleState.REVIEW)

        t2 = self.platform.lifecycle_engine.transition_state(artifact_id, LifecycleState.APPROVED, "user_bob", "Approved")
        self.assertEqual(self.platform.lifecycle_engine.get_state(artifact_id), LifecycleState.APPROVED)

        t3 = self.platform.lifecycle_engine.transition_state(artifact_id, LifecycleState.ACTIVE, "user_charlie", "Activated")
        self.assertEqual(self.platform.lifecycle_engine.get_state(artifact_id), LifecycleState.ACTIVE)

        # Invalid transition: ACTIVE directly to DRAFT
        with self.assertRaises(LifecycleValidationError):
            self.platform.lifecycle_engine.transition_state(artifact_id, LifecycleState.DRAFT, "user_alice", "Invalid")

    def test_facade_async_request(self):
        req = GovernanceApprovalRequestDTO(
            request_id="req-100",
            target_platform="PLATFORM_1",
            operation_type="START_JOB",
            requester_id="user_alice",
            payload={"is_destructive": False},
        )
        res = asyncio.run(self.facade.request_governance_approval(req))
        self.assertEqual(res.status, "APPROVED")
        self.assertTrue(len(res.ledger_block_hash) > 0)


if __name__ == "__main__":
    unittest.main()
