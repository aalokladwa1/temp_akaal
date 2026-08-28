"""tests.security.test_domain_25_to_32_execution_seal_and_audit
=============================================================
Hostile security tests for Execution Seal, Asymmetric Token Minting, Audit Hash Chain, and Threat Detection (Domains 25-32).
"""

import pytest
from akaal.core.time_authority import TimeAuthority
from akaalPipeline.contracts.enums import AuditDecision, KeyAlgorithm, KeyPurpose, SecurityAlertSeverity
from akaalPipeline.events.audit import AuditIntegrityViolationError, SecurityAuditService
from akaalPipeline.security.config import SecurityBaselineConfig
from akaalPipeline.security.detection import SecurityThreatDetector
from akaalPipeline.security.execution_authorization import (
    ExecutionAuthorizationError,
    ExecutionAuthorizationMinter,
    verify_execution_authorization,
)
from akaalPipeline.security.keystore import KeyStoreAuthority
from akaalPipeline.security.seal import ExecutionSealBuilder
from akaalPipeline.state.repositories import (
    SQLiteKeyringRepository,
    SQLiteSecurityAuditRepository,
)
from akaalPipeline.state.unit_of_work import SQLiteUnitOfWork


@pytest.fixture
def seal_and_audit_fixture():
    uow = SQLiteUnitOfWork(db_path=":memory:")
    conn = uow.connection

    keyring_repo = SQLiteKeyringRepository(conn)
    audit_repo = SQLiteSecurityAuditRepository(conn)

    mrk = b"\x03" * 32
    keystore = KeyStoreAuthority(keyring_repo, master_root_key=mrk)
    keystore.initialize_purpose_keys_if_missing()

    audit_service = SecurityAuditService(audit_repo)
    threat_detector = SecurityThreatDetector()
    minter = ExecutionAuthorizationMinter(keystore)

    return {
        "uow": uow,
        "keystore": keystore,
        "audit_repo": audit_repo,
        "audit_service": audit_service,
        "threat_detector": threat_detector,
        "minter": minter,
    }


def test_execution_seal_deterministic_fingerprint():
    seal1 = ExecutionSealBuilder.build_seal(
        tenant_id="tenant-1",
        workspace_id="ws-1",
        project_id="prj-1",
        migration_id="mig-1",
        plan_id="plan-1",
        plan_revision=1,
        execution_mode="M1",
        source_identity_fp="src-fp-1",
        target_identity_fp="tgt-fp-1",
        selection_scope_fp="scope-fp-1",
        config_fp="cfg-fp-1",
        initialization_fp="init-fp-1",
        approval_fp="appr-fp-1",
        fence_epoch=1,
    )

    seal2 = ExecutionSealBuilder.build_seal(
        tenant_id="tenant-1",
        workspace_id="ws-1",
        project_id="prj-1",
        migration_id="mig-1",
        plan_id="plan-1",
        plan_revision=1,
        execution_mode="M1",
        source_identity_fp="src-fp-1",
        target_identity_fp="tgt-fp-1",
        selection_scope_fp="scope-fp-1",
        config_fp="cfg-fp-1",
        initialization_fp="init-fp-1",
        approval_fp="appr-fp-1",
        fence_epoch=1,
    )

    # Identical 14-dimension seals yield exact byte-for-byte matching fingerprints
    assert seal1.seal_fingerprint == seal2.seal_fingerprint

    # Tampering any single dimension (e.g. fence_epoch) alters fingerprint
    seal_tampered = ExecutionSealBuilder.build_seal(
        tenant_id="tenant-1",
        workspace_id="ws-1",
        project_id="prj-1",
        migration_id="mig-1",
        plan_id="plan-1",
        plan_revision=1,
        execution_mode="M1",
        source_identity_fp="src-fp-1",
        target_identity_fp="tgt-fp-1",
        selection_scope_fp="scope-fp-1",
        config_fp="cfg-fp-1",
        initialization_fp="init-fp-1",
        approval_fp="appr-fp-1",
        fence_epoch=2,  # Changed
    )
    assert seal1.seal_fingerprint != seal_tampered.seal_fingerprint


def test_asymmetric_execution_authorization_minting_and_tamper_detection(seal_and_audit_fixture):
    minter = seal_and_audit_fixture["minter"]
    keystore = seal_and_audit_fixture["keystore"]

    seal = ExecutionSealBuilder.build_seal(
        tenant_id="tenant-1",
        workspace_id="ws-1",
        project_id="prj-1",
        migration_id="mig-1",
        plan_id="plan-1",
        plan_revision=1,
        execution_mode="M1",
        source_identity_fp="src-fp-1",
        target_identity_fp="tgt-fp-1",
        selection_scope_fp="scope-fp-1",
        config_fp="cfg-fp-1",
        initialization_fp="init-fp-1",
        approval_fp="appr-fp-1",
        fence_epoch=1,
    )

    artifact = minter.mint_authorization(
        tenant_id="tenant-1",
        workspace_id="ws-1",
        project_id="prj-1",
        migration_id="mig-1",
        execution_id="exec-1",
        execution_seal=seal,
        allowed_operations=["schema_prep", "data_transport"],
        allowed_target_schemas=["public"],
        security_revision=1,
        ttl_seconds=3600,
    )

    pub_pem = keystore.get_public_key_pem(artifact["key_id"])

    # 1. Valid signature verification succeeds
    assert verify_execution_authorization(artifact, pub_pem, "tenant-1", "mig-1") is True

    # 2. Tampering payload (e.g. allowed operations escalation) causes digital signature verification failure
    tampered = dict(artifact)
    tampered["allowed_operations"] = ["schema_prep", "data_transport", "UNAUTHORIZED_ADMIN_DROP"]
    with pytest.raises(ExecutionAuthorizationError, match="signature verification failed"):
        verify_execution_authorization(tampered, pub_pem, "tenant-1", "mig-1")

    # 3. Mismatched tenant fails
    with pytest.raises(ExecutionAuthorizationError, match="Tenant mismatch"):
        verify_execution_authorization(artifact, pub_pem, "foreign-tenant", "mig-1")


def test_tamper_evident_audit_ledger_hash_chain(seal_and_audit_fixture):
    audit_service = seal_and_audit_fixture["audit_service"]
    audit_repo = seal_and_audit_fixture["audit_repo"]
    uow = seal_and_audit_fixture["uow"]

    # 1. Append sequential audit events
    audit_service.record_event(
        tenant_id="tenant-1",
        actor_id="usr-1",
        actor_type="HUMAN",
        event_type="AUTH_LOGIN",
        resource_type="SESSION",
        resource_id="sess-1",
        action="login",
        decision=AuditDecision.LOGIN_SUCCESS,
        details={"ip": "127.0.0.1"},
    )
    audit_service.record_event(
        tenant_id="tenant-1",
        actor_id="usr-1",
        actor_type="HUMAN",
        event_type="MIGRATION_CREATE",
        resource_type="MIGRATION",
        resource_id="mig-1",
        action="migration.create",
        decision=AuditDecision.MUTATE,
        details={"name": "Alpha Migration"},
    )
    audit_service.record_event(
        tenant_id="tenant-1",
        actor_id="usr-1",
        actor_type="HUMAN",
        event_type="MIGRATION_START",
        resource_type="MIGRATION",
        resource_id="mig-1",
        action="migration.start",
        decision=AuditDecision.ALLOW,
        details={"fence_epoch": 1},
    )

    # 2. Hash chain integrity passes
    assert audit_service.verify_ledger_integrity("tenant-1") is True

    # 3. Tampering interior row payload causes hash chain break
    uow.connection.execute(
        "UPDATE security_audit_ledger SET decision = 'DENY' WHERE tenant_id = 'tenant-1' AND sequence_number = 2"
    )
    with pytest.raises(AuditIntegrityViolationError, match="entry hash mismatch"):
        audit_service.verify_ledger_integrity("tenant-1")


def test_security_threat_detector_alerting(seal_and_audit_fixture):
    threat_detector = seal_and_audit_fixture["threat_detector"]

    # 1. Brute force alert
    alert_bf = threat_detector.record_auth_failure("tenant-1", "attacker", "192.168.1.100", 5)
    assert alert_bf is not None
    assert alert_bf.threat_type == "BRUTE_FORCE_AUTHENTICATION_ATTEMPT"
    assert alert_bf.severity == SecurityAlertSeverity.HIGH

    # 2. Cross-tenant IDOR probing alert
    alert_idor = threat_detector.record_cross_tenant_access_attempt("tenant-attacker", "tenant-victim", "mig-999", "usr-mallory")
    assert alert_idor.threat_type == "CROSS_TENANT_IDOR_PROBING"
    assert alert_idor.severity == SecurityAlertSeverity.CRITICAL

    # 3. Seal tampering alert
    alert_seal = threat_detector.record_seal_tamper_attempt("tenant-1", "mig-1", "expected-fp", "tampered-fp")
    assert alert_seal.threat_type == "EXECUTION_SEAL_INTEGRITY_VIOLATION"
    assert alert_seal.severity == SecurityAlertSeverity.CRITICAL

    # 4. Zombie worker / stale fencing epoch alert
    alert_zombie = threat_detector.record_fencing_epoch_violation("tenant-1", "mig-1", 1, 3)
    assert alert_zombie.threat_type == "ZOMBIE_WORKER_STALE_FENCING_EPOCH"
    assert alert_zombie.severity == SecurityAlertSeverity.CRITICAL
