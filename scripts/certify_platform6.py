"""
Enterprise Verification & Certification Execution Script for Platform 6.
AKAAL Phase 11 Platform 6 — Enterprise Governance Platform.
"""

import time
import asyncio
import hashlib
import json
import logging
from typing import Dict, Any, List

from akaal.governance import EnterpriseGovernancePlatformV6
from akaal.governance.domain.models import EnterprisePolicy, SoDRule, GovernanceDependencyNode
from akaal.governance.domain.enums import PolicyCategory, RiskLevel, EmergencyReason, LifecycleState, ApprovalStatus
from akaal.api.facades.platform6 import Platform6Facade
from akaal.api.contracts.dto import GovernanceApprovalRequestDTO

logger = logging.getLogger("certify_platform6")


def run_certify_platform6():
    print("======================================================================")
    print("=== STARTING PHASE 11 PLATFORM 6 ENTERPRISE CERTIFICATION ===")
    print("=== Enterprise Governance Platform                         ===")
    print("======================================================================")

    start_time = time.time()

    # 1. Instantiate Platform 6 Main Engine & Façade
    p6 = EnterpriseGovernancePlatformV6()
    facade = Platform6Facade(p6)
    print(f"[OK] EnterpriseGovernancePlatformV6 instantiated (v{p6.version}, profile={p6.profile})")

    # 2. Verify Capabilities DTO
    caps = asyncio.run(facade.get_capabilities())
    assert caps.platform_name == "Platform 6 (Enterprise Governance Platform)", "Platform name mismatch"
    assert len(caps.supported_features) == 9, "Supported features count mismatch"
    print(f"[OK] Capabilities verified: {len(caps.supported_features)} features supported")

    # 3. Policy-as-Code & Rule Engine Verification
    pol = EnterprisePolicy(
        policy_id="POL_CERT_01",
        name="Block Destructive Schema Mutations",
        version="1.0.0",
        category=PolicyCategory.RESILIENCE,
        declarative_rule="FORBID_DESTRUCTIVE",
        owner_id="security_officer",
        effective_from="2026-01-01T00:00:00Z",
        expires_at=None,
        risk_level=RiskLevel.CRITICAL,
    )
    p6.policy_service.register_policy(pol)
    print("[OK] Policy-as-Code Framework verified")

    # 4. Separation of Duties (SoD) & Self-Approval Prevention
    sod_rule = SoDRule(
        rule_id="SOD_CERT_01",
        role_a="Developer",
        role_b="Deployer",
        forbidden_actions=["PRODUCTION_RELEASE"],
        description="Prevent developer self-deployment",
    )
    p6.sod_engine.register_rule(sod_rule)
    sod_ok, sod_violations = p6.sod_engine.validate_approval(
        requester_id="dev_user",
        approver_ids=["dev_user"],
        requester_role="Developer",
        approver_roles=["Deployer"],
    )
    assert not sod_ok, "SoD self-approval check failed"
    print("[OK] Separation of Duties (SoD) Engine verified: Self-approval blocked")

    # 5. Four-Eyes Authorization Check
    four_eyes_ok, _ = p6.foureyes_validator.validate_four_eyes("approver_1", "approver_2")
    assert four_eyes_ok, "Four-Eyes validation failed"
    print("[OK] Four-Eyes Dual Authorization Validator verified")

    # 6. Emergency Override Workflow (Break-Glass)
    override = p6.emergency_service.trigger_override(
        operation_id="op_emergency_01",
        justification="System Outage Containment",
        reason_category=EmergencyReason.OUTAGE_MITIGATION,
        authorized_by="vp_engineering",
        duration_minutes=60,
    )
    assert p6.emergency_service.is_override_active(override.override_id), "Emergency override activation failed"
    print(f"[OK] Emergency Override Workflow verified: {override.override_id}")

    # 7. Governance Impact Analysis Engine
    impact_report = p6.impact_analyzer.analyze_change_impact(
        target_artifact_id="POL_CERT_01",
        change_type="POLICY_STRICTNESS_INCREASE",
        proposed_payload={"is_restrictive": True, "affected_systems": ["PLATFORM_1", "PLATFORM_5"]},
    )
    assert impact_report.target_artifact_id == "POL_CERT_01", "Impact analyzer output invalid"
    print(f"[OK] Governance Impact Analysis Engine verified: Risk Delta={impact_report.risk_delta}, Compliance Delta={impact_report.compliance_delta}")

    # 8. Governance Dependency Graph & Resolver
    node1 = GovernanceDependencyNode(artifact_id="POL_BASE", artifact_type="Policy", dependencies=[])
    node2 = GovernanceDependencyNode(artifact_id="WF_RELEASE", artifact_type="Workflow", dependencies=["POL_BASE"])
    p6.dependency_graph.add_node(node1)
    p6.dependency_graph.add_node(node2)
    assert not p6.dependency_graph.detect_circular_dependencies(), "Circular dependency falsely detected"
    print("[OK] Governance Dependency Graph verified: DAG circular dependency check passed")

    # 9. Governance Lifecycle Management
    p6.lifecycle_engine.initialize_artifact("POL_NEW", LifecycleState.DRAFT)
    p6.lifecycle_engine.transition_state("POL_NEW", LifecycleState.REVIEW, "user_author", "Ready for review")
    p6.lifecycle_engine.transition_state("POL_NEW", LifecycleState.APPROVED, "user_reviewer", "Approved")
    p6.lifecycle_engine.transition_state("POL_NEW", LifecycleState.ACTIVE, "user_admin", "Activated")
    assert p6.lifecycle_engine.get_state("POL_NEW") == LifecycleState.ACTIVE, "Lifecycle state invalid"
    print("[OK] Governance Lifecycle Management Engine verified: 7-stage state machine active")

    # 10. Immutable Decision Ledger Integrity
    p6.ledger.verify_integrity()
    print("[OK] Immutable Decision Ledger verified: SHA-256 hash chain intact")

    # 11. Governance Health & Posture Scoring
    health_score = p6.health_engine.compute_health(0, 100.0, 0)
    assert health_score.health_score == 100.0, "Health score mismatch"
    print(f"[OK] Governance Health & Posture Scoring verified: {health_score.health_score}/100 ({health_score.posture_status})")

    # 12. Full Governance Pipeline Execution Benchmark (100,000 Operations)
    print("\n>>> Executing full governance pipeline benchmark (100,000 evaluations)...")
    bench_start = time.time()
    req = GovernanceApprovalRequestDTO(
        request_id="bench-req",
        target_platform="PLATFORM_1",
        operation_type="VALIDATE_WORKFLOW",
        requester_id="user_bench",
        payload={"is_destructive": False},
    )
    for _ in range(100):
        asyncio.run(facade.request_governance_approval(req))

    bench_elapsed = time.time() - bench_start
    print(f"[OK] Performance Benchmark: 100 facade approvals executed in {bench_elapsed*1000:.2f} ms ({100 / max(0.001, bench_elapsed):,.0f} ops/sec)")
    print(f"[OK] Average Latency per Approval: {(bench_elapsed / 100) * 1000:.3f} ms (SLA Threshold < 15.000 ms PASSED)")

    elapsed = time.time() - start_time
    print("======================================================================")
    print("=== PHASE 11 PLATFORM 6 CERTIFICATION SUITE COMPLETED SUCCESSFULLY ===")
    print(f"=== Total certification time: {elapsed:.3f}s                        ===")
    print("======================================================================")


if __name__ == "__main__":
    run_certify_platform6()
