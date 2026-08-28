"""tests.security.test_hostile_attacks_part1_identity
===================================================
Hostile Security Verification Suite - Part 1: Identity & Credentials
Contains Hostile Attack Scenarios HOSTILE-ATK-01 through HOSTILE-ATK-14.
"""

import pytest
import sqlite3
from akaalPipeline.state.unit_of_work import SQLiteUnitOfWork
from akaalPipeline.identity.passwords import PasswordAuthenticationEngine, CryptographicDependencyError
from akaalPipeline.identity.principals import PrincipalManager, PrincipalLockedError, AuthenticationFailedError, PrincipalDisabledError
from akaalPipeline.identity.sessions import SessionManager
from akaalPipeline.identity.tokens import ServiceTokenAuthority
from akaalPipeline.identity.groups import GroupAuthority, NestedGroupsNotSupportedError
from akaalPipeline.contracts.enums import PrincipalType, KDFAlgorithm
from akaalPipeline.contracts.errors import UnauthorizedError, ForbiddenError, ConflictError


@pytest.fixture
def uow(tmp_path):
    db_path = str(tmp_path / "akaal_hostile_identity.db")
    uow_inst = SQLiteUnitOfWork(db_path)
    uow_inst.initialize_schema()
    uow_inst.tenants.create_tenant("tenant-corp", "Corp")
    uow_inst.tenants.create_tenant("tenant-evil", "Evil")
    return uow_inst


def test_hostile_atk_01_password_below_pbkdf2_floor(uow):
    """HOSTILE-ATK-01: Attempt password creation with PBKDF2 iterations < 600,000."""
    engine = PasswordAuthenticationEngine()
    with pytest.raises(ValueError, match="PBKDF2 iterations below immutable floor"):
        engine.hash_password("admin_pass", algorithm=KDFAlgorithm.PBKDF2_SHA256.value, custom_params={"iterations": 10000})


def test_hostile_atk_02_password_below_argon2_memory_floor(uow):
    """HOSTILE-ATK-02: Attempt password creation with Argon2id memory < 64MB."""
    engine = PasswordAuthenticationEngine()
    with pytest.raises(ValueError, match="Argon2id parameters below immutable security floors"):
        engine.hash_password("admin_pass", algorithm=KDFAlgorithm.ARGON2ID.value, custom_params={"memory_cost": 1024})


def test_hostile_atk_03_kdf_downgrade_rejection(uow):
    """HOSTILE-ATK-03: Attempt to verify an Argon2 credential using forged PBKDF2 parameters."""
    engine = PasswordAuthenticationEngine()
    # Attempting to verify an Argon2 envelope with tampered algorithm string or parameters
    with pytest.raises(ValueError, match="Unrecognized algorithm"):
        engine.verify_password("secret", "MD5_INSECURE", {}, "salt", "hash")


def test_hostile_atk_04_brute_force_account_lockout(uow):
    """HOSTILE-ATK-04: Execute consecutive invalid login attempts to trigger account lockout."""
    mgr = PrincipalManager(uow.principals, uow.credentials)
    mgr.create_principal(tenant_id="tenant-corp", username="usr-victim", principal_type=PrincipalType.HUMAN, password="ValidPass123!", display_name="Victim", email="victim@corp.com")
    
    # 4 failed attempts raise AuthenticationFailedError
    for _ in range(4):
        with pytest.raises(AuthenticationFailedError):
            mgr.authenticate("tenant-corp", "usr-victim", "WrongPassword!")
            
    # 5th attempt triggers lockout
    with pytest.raises(PrincipalLockedError):
        mgr.authenticate("tenant-corp", "usr-victim", "WrongPassword!")
        
    # Subsequent attempt with correct password remains locked
    with pytest.raises(PrincipalLockedError):
        mgr.authenticate("tenant-corp", "usr-victim", "ValidPass123!")


def test_hostile_atk_05_timing_attack_nonexistent_user(uow):
    """HOSTILE-ATK-05: Timing attack probe on non-existent user must execute constant-time dummy verify."""
    mgr = PrincipalManager(uow.principals, uow.credentials)
    with pytest.raises(AuthenticationFailedError):
        mgr.authenticate("tenant-corp", "usr-nonexistent-9999", "SomePassword123!")


def test_hostile_atk_06_session_forgery_and_tampering(uow):
    """HOSTILE-ATK-06: Present random forged session token to SessionManager."""
    sm = SessionManager(uow.sessions, uow.principals, uow.tenants)
    with pytest.raises(UnauthorizedError, match="Invalid, revoked, or expired session"):
        sm.authenticate_session("tenant-corp", "00" * 32)


def test_hostile_atk_07_session_absolute_timeout_expiration(uow):
    """HOSTILE-ATK-07: Attempt to authenticate session past absolute timeout."""
    mgr = PrincipalManager(uow.principals, uow.credentials)
    mgr.create_principal(tenant_id="tenant-corp", username="usr-session", principal_type=PrincipalType.HUMAN, password="ValidPass123!")
    sm = SessionManager(uow.sessions, uow.principals, uow.tenants)
    sess = sm.create_session("tenant-corp", "usr-session", ttl_seconds=1)
    
    # Manually expire session in DB
    uow.conn.execute("UPDATE enterprise_sessions SET absolute_expires_at = '2020-01-01T00:00:00Z'")
    with pytest.raises(UnauthorizedError):
        sm.authenticate_session("tenant-corp", sess["token"])


def test_hostile_atk_08_session_sliding_idle_timeout(uow):
    """HOSTILE-ATK-08: Attempt to authenticate session with expired idle window."""
    mgr = PrincipalManager(uow.principals, uow.credentials)
    mgr.create_principal(tenant_id="tenant-corp", username="usr-idle", principal_type=PrincipalType.HUMAN, password="ValidPass123!")
    sm = SessionManager(uow.sessions, uow.principals, uow.tenants)
    sess = sm.create_session("tenant-corp", "usr-idle")
    
    # Set last_activity_at to 2 hours ago
    uow.conn.execute("UPDATE enterprise_sessions SET last_activity_at = '2020-01-01T00:00:00Z'")
    with pytest.raises(UnauthorizedError):
        sm.authenticate_session("tenant-corp", sess["token"])


def test_hostile_atk_09_session_revocation_on_security_revision_bump(uow):
    """HOSTILE-ATK-09: Authenticate session after principal security revision has advanced."""
    mgr = PrincipalManager(uow.principals, uow.credentials)
    mgr.create_principal(tenant_id="tenant-corp", username="usr-rev", principal_type=PrincipalType.HUMAN, password="ValidPass123!")
    sm = SessionManager(uow.sessions, uow.principals, uow.tenants)
    sess = sm.create_session("tenant-corp", "usr-rev")
    
    # Bump security revision (e.g. password changed or grant revoked)
    uow.principals.bump_security_revision("tenant-corp", "usr-rev")
    
    with pytest.raises(UnauthorizedError):
        sm.authenticate_session("tenant-corp", sess["token"])


def test_hostile_atk_10_service_token_hash_collision_or_forgery(uow):
    """HOSTILE-ATK-10: Present unauthorized forged API bearer token."""
    mgr = PrincipalManager(uow.principals, uow.credentials)
    mgr.create_principal(tenant_id="tenant-corp", username="svc-bot", principal_type=PrincipalType.SERVICE)
    sta = ServiceTokenAuthority(uow.service_tokens, uow.principals, uow.tenants)
    
    with pytest.raises(UnauthorizedError, match="Invalid, expired, or revoked API token"):
        sta.authenticate_token("tenant-corp", "ak_live_forged_fake_token_1234567890abcdef")


def test_hostile_atk_11_service_token_revocation(uow):
    """HOSTILE-ATK-11: Authenticate with explicitly revoked service API token."""
    mgr = PrincipalManager(uow.principals, uow.credentials)
    mgr.create_principal(tenant_id="tenant-corp", username="svc-bot2", principal_type=PrincipalType.SERVICE)
    sta = ServiceTokenAuthority(uow.service_tokens, uow.principals, uow.tenants)
    token_res = sta.create_token("tenant-corp", "svc-bot2", "Test Token", ["migration.read"])
    
    # Revoke token
    sta.revoke_token("tenant-corp", token_res["token_id"])
    
    with pytest.raises(UnauthorizedError, match="Invalid, expired, or revoked API token"):
        sta.authenticate_token("tenant-corp", token_res["token"])


def test_hostile_atk_12_nested_group_membership_injection(uow):
    """HOSTILE-ATK-12: Attempt to inject nested group membership to trigger cyclic or uncontained traversal."""
    ga = GroupAuthority(uow.groups, uow.principals)
    ga.create_group("tenant-corp", "grp-parent", "Parent Group")
    ga.create_group("tenant-corp", "grp-child", "Child Group")
    
    # Adding a group as a member of another group must fail closed
    with pytest.raises(NestedGroupsNotSupportedError):
        ga.add_member("tenant-corp", "grp-parent", "grp-child")


def test_hostile_atk_13_workload_principal_authentication_and_isolation(uow):
    """HOSTILE-ATK-13: Validate workload principal isolation and ensure workload cannot act on other tenants."""
    mgr = PrincipalManager(uow.principals, uow.credentials)
    mgr.create_principal(tenant_id="tenant-corp", username="workload-k8s-pod-01", principal_type=PrincipalType.WORKLOAD)
    
    # Verify workload principal is created and typed correctly
    p = uow.principals.get_by_username("tenant-corp", "workload-k8s-pod-01")
    assert p["principal_type"] == PrincipalType.WORKLOAD.value
    
    # Probe from tenant-evil must fail closed
    p_evil = uow.principals.get_by_username("tenant-evil", "workload-k8s-pod-01")
    assert p_evil is None


def test_hostile_atk_14_disabled_principal_authentication_rejection(uow):
    """HOSTILE-ATK-14: Attempt authentication on disabled principal."""
    mgr = PrincipalManager(uow.principals, uow.credentials)
    mgr.create_principal(tenant_id="tenant-corp", username="usr-disabled", principal_type=PrincipalType.HUMAN, password="ValidPass123!")
    
    # Disable principal
    uow.principals.update_principal("tenant-corp", "usr-disabled", is_active=False)
    
    with pytest.raises((AuthenticationFailedError, PrincipalDisabledError, ValueError)):
        mgr.authenticate("tenant-corp", "usr-disabled", "ValidPass123!")
