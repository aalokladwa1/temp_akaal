"""tests.security.test_hostile_attacks_part4_execution_seal_audit
==============================================================
Hostile Security Verification Suite - Part 4: Execution Seal, Asymmetric Tokens & Audit
Contains Hostile Attack Scenarios HOSTILE-ATK-41 through HOSTILE-ATK-52.
"""

import pytest
from akaalPipeline.state.unit_of_work import SQLiteUnitOfWork
from akaalPipeline.security.seal import ExecutionSealBuilder, ExecutionSeal
from akaalPipeline.security.execution_authorization import (
    ExecutionAuthorizationMinter,
    verify_execution_authorization,
    ExecutionAuthorizationError,
    ExecutionAuthorizationReplayError,
    ExecutionReplayCache,
)
from akaalPipeline.security.keystore import KeyStoreAuthority
from akaalPipeline.security.cache import AuthorizationCacheManager
from akaalPipeline.events.audit import SecurityAuditService, AuditIntegrityViolationError
from akaalPipeline.security.detection import SecurityThreatDetector
from akaalPipeline.contracts.enums import KeyPurpose, AuditDecision


@pytest.fixture
def uow(tmp_path):
    db_path = str(tmp_path / "akaal_hostile_seal_audit.db")
    uow_inst = SQLiteUnitOfWork(db_path)
    uow_inst.initialize_schema()
    uow_inst.tenants.create_tenant("tenant-corp", "Corp")
    return uow_inst


def test_hostile_atk_41_cache_invalidation_on_security_revision_advance(uow):
    """HOSTILE-ATK-41: CacheManager must instantly invalidate authorization decisions when security revision advances."""
    cache = AuthorizationCacheManager()
    cache.set_decision("tenant-corp", "usr-alice", 1, "migration.execute", "PROJECT", "proj-1", True)
    
    # Hit cache at revision 1
    assert cache.get_decision("tenant-corp", "usr-alice", 1, "migration.execute", "PROJECT", "proj-1") is True
    
    # Query at revision 2 (after permission change) -> Cache Miss
    assert cache.get_decision("tenant-corp", "usr-alice", 2, "migration.execute", "PROJECT", "proj-1") is None


def test_hostile_atk_42_execution_seal_14_dimension_tampering():
    """HOSTILE-ATK-42: Modify any 1 of 14 execution seal dimensions and verify fingerprint mismatch."""
    seal1 = ExecutionSealBuilder.build_seal(
        tenant_id="tenant-corp", workspace_id="ws-01", project_id="proj-01",
        migration_id="mig-01", plan_id="plan-01", plan_revision=1,
        execution_mode="M1", source_identity_fingerprint="src_fp",
        target_identity_fingerprint="tgt_fp", selection_scope_fingerprint="sel_fp",
        config_fingerprint="cfg_fp", initialization_fingerprint="init_fp",
        approval_fingerprint="appr_fp", fence_epoch=10,
    )
    
    # Tamper with fence_epoch (10 -> 11)
    seal2 = ExecutionSealBuilder.build_seal(
        tenant_id="tenant-corp", workspace_id="ws-01", project_id="proj-01",
        migration_id="mig-01", plan_id="plan-01", plan_revision=1,
        execution_mode="M1", source_identity_fingerprint="src_fp",
        target_identity_fingerprint="tgt_fp", selection_scope_fingerprint="sel_fp",
        config_fingerprint="cfg_fp", initialization_fingerprint="init_fp",
        approval_fingerprint="appr_fp", fence_epoch=11,
    )
    assert seal1.seal_fingerprint != seal2.seal_fingerprint


def test_hostile_atk_43_asymmetric_token_signature_tampering(uow):
    """HOSTILE-ATK-43: Tamper with signed execution authorization payload and verify Ed25519 rejection."""
    mrk = b"01234567890123456789012345678901"
    ks = KeyStoreAuthority(uow.keyring, master_root_key=mrk)
    minter = ExecutionAuthorizationMinter(ks)
    
    seal = ExecutionSealBuilder.build_seal(
        tenant_id="tenant-corp", workspace_id="ws-01", project_id="proj-01",
        migration_id="mig-01", plan_id="plan-01", plan_revision=1,
        execution_mode="M1", source_identity_fingerprint="src", target_identity_fingerprint="tgt",
        selection_scope_fingerprint="sel", config_fingerprint="cfg",
        initialization_fingerprint="init", approval_fingerprint="appr", fence_epoch=1,
    )
    
    artifact = minter.mint_authorization(
        tenant_id="tenant-corp", workspace_id="ws-01", project_id="proj-01",
        migration_id="mig-01", execution_id="exec-01", execution_seal=seal,
        allowed_operations=["MIGRATE_BULK"], allowed_target_schemas=["public"],
        security_revision=1,
    )
    
    pub_pem = ks.get_public_key_pem(artifact["key_id"])
    
    # Tamper payload: escalate allowed_operations
    artifact["allowed_operations"] = ["MIGRATE_BULK", "DROP_DATABASE"]
    
    with pytest.raises(ExecutionAuthorizationError, match="signature verification failed"):
        verify_execution_authorization(artifact, pub_pem, expected_tenant_id="tenant-corp")


def test_hostile_atk_44_execution_token_nonce_replay(uow):
    """HOSTILE-ATK-44: Present the same execution authorization artifact twice to verify replay detection."""
    mrk = b"01234567890123456789012345678901"
    ks = KeyStoreAuthority(uow.keyring, master_root_key=mrk)
    minter = ExecutionAuthorizationMinter(ks)
    
    seal = ExecutionSealBuilder.build_seal(
        tenant_id="tenant-corp", workspace_id="ws-01", project_id="proj-01",
        migration_id="mig-01", plan_id="plan-01", plan_revision=1,
        execution_mode="M1", source_identity_fingerprint="src", target_identity_fingerprint="tgt",
        selection_scope_fingerprint="sel", config_fingerprint="cfg",
        initialization_fingerprint="init", approval_fingerprint="appr", fence_epoch=1,
    )
    
    artifact = minter.mint_authorization(
        tenant_id="tenant-corp", workspace_id="ws-01", project_id="proj-01",
        migration_id="mig-01", execution_id="exec-02", execution_seal=seal,
        allowed_operations=["MIGRATE_BULK"], allowed_target_schemas=["public"],
        security_revision=1,
    )
    pub_pem = ks.get_public_key_pem(artifact["key_id"])
    
    cache = ExecutionReplayCache()
    # First verification: OK
    assert verify_execution_authorization(artifact, pub_pem, expected_tenant_id="tenant-corp", replay_cache=cache) is True
    
    # Second verification: Replay Rejection
    with pytest.raises(ExecutionAuthorizationReplayError, match="replay detected"):
        verify_execution_authorization(artifact, pub_pem, expected_tenant_id="tenant-corp", replay_cache=cache)


def test_hostile_atk_45_execution_token_unauthorized_operation_rejection(uow):
    """HOSTILE-ATK-45: Request execution of an operation outside allowed_operations list."""
    mrk = b"01234567890123456789012345678901"
    ks = KeyStoreAuthority(uow.keyring, master_root_key=mrk)
    minter = ExecutionAuthorizationMinter(ks)
    seal = ExecutionSealBuilder.build_seal(
        tenant_id="tenant-corp", workspace_id="ws-01", project_id="proj-01",
        migration_id="mig-01", plan_id="plan-01", plan_revision=1,
        execution_mode="M1", source_identity_fingerprint="src", target_identity_fingerprint="tgt",
        selection_scope_fingerprint="sel", config_fingerprint="cfg",
        initialization_fingerprint="init", approval_fingerprint="appr", fence_epoch=1,
    )
    artifact = minter.mint_authorization(
        tenant_id="tenant-corp", workspace_id="ws-01", project_id="proj-01",
        migration_id="mig-01", execution_id="exec-03", execution_seal=seal,
        allowed_operations=["DISCOVER_CATALOG"], allowed_target_schemas=["public"],
        security_revision=1,
    )
    pub_pem = ks.get_public_key_pem(artifact["key_id"])
    cache = ExecutionReplayCache()
    
    with pytest.raises(ExecutionAuthorizationError, match="not in allowed operations"):
        verify_execution_authorization(
            artifact, pub_pem, expected_tenant_id="tenant-corp",
            expected_operation="EXECUTE_BULK_MIGRATION", replay_cache=cache
        )


def test_hostile_atk_46_execution_token_unauthorized_target_schema(uow):
    """HOSTILE-ATK-46: Request execution on target schema outside allowed_target_schemas list."""
    mrk = b"01234567890123456789012345678901"
    ks = KeyStoreAuthority(uow.keyring, master_root_key=mrk)
    minter = ExecutionAuthorizationMinter(ks)
    seal = ExecutionSealBuilder.build_seal(
        tenant_id="tenant-corp", workspace_id="ws-01", project_id="proj-01",
        migration_id="mig-01", plan_id="plan-01", plan_revision=1,
        execution_mode="M1", source_identity_fingerprint="src", target_identity_fingerprint="tgt",
        selection_scope_fingerprint="sel", config_fingerprint="cfg",
        initialization_fingerprint="init", approval_fingerprint="appr", fence_epoch=1,
    )
    artifact = minter.mint_authorization(
        tenant_id="tenant-corp", workspace_id="ws-01", project_id="proj-01",
        migration_id="mig-01", execution_id="exec-04", execution_seal=seal,
        allowed_operations=["MIGRATE_BULK"], allowed_target_schemas=["app_data"],
        security_revision=1,
    )
    pub_pem = ks.get_public_key_pem(artifact["key_id"])
    cache = ExecutionReplayCache()
    
    with pytest.raises(ExecutionAuthorizationError, match="not in allowed schemas"):
        verify_execution_authorization(
            artifact, pub_pem, expected_tenant_id="tenant-corp",
            expected_target_schema="super_secret_schema", replay_cache=cache
        )


def test_hostile_atk_47_audit_hash_chain_genesis_and_continuation(uow):
    """HOSTILE-ATK-47: Validate SHA-256 hash chaining links entries deterministically."""
    audit = SecurityAuditService(uow.audit_ledger)
    e1 = audit.record_event("tenant-corp", "usr-admin", "HUMAN", "LOGIN", "SYSTEM", "root", "login", AuditDecision.LOGIN_SUCCESS.value, {})
    e2 = audit.record_event("tenant-corp", "usr-admin", "HUMAN", "MIGRATE", "MIGRATION", "mig-1", "start", AuditDecision.ALLOW.value, {})
    
    assert e1["previous_hash"] == "0" * 64
    assert e2["previous_hash"] == e1["entry_hash"]
    assert audit.verify_ledger_integrity("tenant-corp") is True


def test_hostile_atk_48_audit_ledger_interior_row_tampering(uow):
    """HOSTILE-ATK-48: Tamper with details of an interior audit row and verify hash chain detects modification."""
    audit = SecurityAuditService(uow.audit_ledger)
    audit.record_event("tenant-corp", "usr-1", "HUMAN", "OP1", "RES", "1", "act1", AuditDecision.ALLOW.value, {})
    e2 = audit.record_event("tenant-corp", "usr-2", "HUMAN", "OP2", "RES", "2", "act2", AuditDecision.ALLOW.value, {})
    audit.record_event("tenant-corp", "usr-3", "HUMAN", "OP3", "RES", "3", "act3", AuditDecision.ALLOW.value, {})
    
    # Tamper with row 2 decision directly in SQLite
    uow.conn.execute("UPDATE security_audit_ledger SET decision = 'DENY' WHERE audit_id = ?", (e2["audit_id"],))
    
    with pytest.raises(AuditIntegrityViolationError):
        audit.verify_ledger_integrity("tenant-corp")


def test_hostile_atk_49_audit_ledger_row_deletion_or_gap(uow):
    """HOSTILE-ATK-49: Delete an interior audit row and verify sequence gap violation."""
    audit = SecurityAuditService(uow.audit_ledger)
    audit.record_event("tenant-corp", "usr-1", "HUMAN", "OP1", "RES", "1", "act1", AuditDecision.ALLOW.value, {})
    e2 = audit.record_event("tenant-corp", "usr-2", "HUMAN", "OP2", "RES", "2", "act2", AuditDecision.ALLOW.value, {})
    audit.record_event("tenant-corp", "usr-3", "HUMAN", "OP3", "RES", "3", "act3", AuditDecision.ALLOW.value, {})
    
    # Delete row 2
    uow.conn.execute("DELETE FROM security_audit_ledger WHERE audit_id = ?", (e2["audit_id"],))
    
    with pytest.raises(AuditIntegrityViolationError):
        audit.verify_ledger_integrity("tenant-corp")


def test_hostile_atk_50_threat_detector_brute_force_alerting():
    """HOSTILE-ATK-50: SecurityThreatDetector must raise HIGH severity alert on repeated login failures."""
    detector = SecurityThreatDetector()
    alert = None
    for _ in range(6):
        alert = detector.analyze_event({
            "event_type": "LOGIN_FAILURE",
            "decision": "LOGIN_FAILURE",
            "tenant_id": "tenant-corp",
            "actor_id": "usr-victim",
            "ip_address": "192.168.1.100",
        })
    assert alert is not None
    assert alert.alert_type == "BRUTE_FORCE_AUTHENTICATION_ATTEMPT"
    assert alert.severity == "HIGH"


def test_hostile_atk_51_threat_detector_idor_cross_tenant_probing():
    """HOSTILE-ATK-51: SecurityThreatDetector must raise CRITICAL severity alert on IDOR cross-tenant probing."""
    detector = SecurityThreatDetector()
    alert = detector.analyze_event({
        "event_type": "CROSS_TENANT_IDOR_PROBING",
        "decision": "DENY",
        "tenant_id": "tenant-corp",
        "actor_id": "usr-attacker",
        "target_tenant_id": "tenant-victim",
    })
    assert alert is not None
    assert alert.alert_type == "CROSS_TENANT_IDOR_PROBING"
    assert alert.severity == "CRITICAL"


def test_hostile_atk_52_threat_detector_zombie_worker_alert():
    """HOSTILE-ATK-52: SecurityThreatDetector must raise CRITICAL severity alert on zombie worker stale epoch."""
    detector = SecurityThreatDetector()
    alert = detector.analyze_event({
        "event_type": "STALE_FENCING_EPOCH",
        "decision": "DENY",
        "tenant_id": "tenant-corp",
        "actor_id": "worker-zombie-01",
        "stale_epoch": 10,
        "authoritative_epoch": 11,
    })
    assert alert is not None
    assert alert.alert_type == "ZOMBIE_WORKER_STALE_FENCING_EPOCH"
    assert alert.severity == "CRITICAL"
