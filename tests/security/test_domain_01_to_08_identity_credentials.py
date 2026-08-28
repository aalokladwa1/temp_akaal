"""tests.security.test_domain_01_to_08_identity_credentials
=========================================================
Hostile security tests for Identity, Passwords, Sessions, Tokens, and Flat Groups (Domains 1-8).
"""

import time
import pytest
from akaal.core.crypto_random import generate_salt_hex, generate_secure_id, generate_secure_token
from akaal.core.time_authority import ClockSkewDetectedError, TimeAuthority
from akaalPipeline.contracts.enums import KDFAlgorithm, PrincipalType
from akaalPipeline.identity.groups import GroupAuthority, NestedGroupsNotSupportedError
from akaalPipeline.identity.passwords import (
    CryptographicDependencyError,
    PasswordAuthenticationEngine,
)
from akaalPipeline.identity.principals import (
    AuthenticationFailedError,
    PrincipalDisabledError,
    PrincipalLockedError,
    PrincipalManager,
)
from akaalPipeline.identity.sessions import (
    SessionExpiredError,
    SessionRevokedError,
    SessionSecurityRevisionMismatchError,
    SessionManager,
)
from akaalPipeline.identity.tokens import (
    ServiceTokenAuthority,
    ServiceTokenExpiredError,
    ServiceTokenNotFoundError,
    ServiceTokenRevokedError,
)
from akaalPipeline.security.config import SecurityBaselineConfig
from akaalPipeline.state.repositories import (
    SQLiteCredentialRepository,
    SQLiteGroupRepository,
    SQLitePrincipalRepository,
    SQLiteSessionRepository,
    SQLiteServiceTokenRepository,
    SQLiteTenantRepository,
)
from akaalPipeline.state.unit_of_work import SQLiteUnitOfWork


@pytest.fixture
def uow():
    unit = SQLiteUnitOfWork(db_path=":memory:")
    # Initialize initial tenant
    tenant_repo = SQLiteTenantRepository(unit.connection)
    tenant_repo.create("tenant-1", "Test Tenant Alpha", "ACTIVE", TimeAuthority.utc_iso_now())
    return unit


def test_password_hashing_and_verification_pbkdf2():
    engine = PasswordAuthenticationEngine()
    algo, params, salt, pwd_hash = engine.hash_password("SuperSecret123!", algorithm=KDFAlgorithm.PBKDF2_SHA256.value)
    assert algo == KDFAlgorithm.PBKDF2_SHA256.value
    assert params["iterations"] >= 600000

    # Valid verify
    assert engine.verify_password("SuperSecret123!", algo, params, salt, pwd_hash) is True
    # Invalid password verify
    assert engine.verify_password("WrongPassword", algo, params, salt, pwd_hash) is False


def test_password_hashing_and_verification_argon2id():
    engine = PasswordAuthenticationEngine()
    algo, params, salt, pwd_hash = engine.hash_password("SuperSecret123!", algorithm=KDFAlgorithm.ARGON2ID.value)
    assert algo == KDFAlgorithm.ARGON2ID.value
    assert params["memory_cost_kib"] >= 65536
    assert params["time_cost"] >= 3

    assert engine.verify_password("SuperSecret123!", algo, params, salt, pwd_hash) is True
    assert engine.verify_password("WrongPassword", algo, params, salt, pwd_hash) is False


def test_password_security_floor_enforcement():
    engine = PasswordAuthenticationEngine()
    # Below PBKDF2 floor (600,000)
    with pytest.raises(ValueError, match="below immutable floor"):
        engine.hash_password("Secret", algorithm=KDFAlgorithm.PBKDF2_SHA256.value, custom_params={"iterations": 10000})

    # Below Argon2 floor (64MB)
    with pytest.raises(ValueError, match="below immutable security floors"):
        engine.hash_password("Secret", algorithm=KDFAlgorithm.ARGON2ID.value, custom_params={"memory_cost": 1024})


def test_principal_lifecycle_and_lockout(uow):
    p_repo = SQLitePrincipalRepository(uow.connection)
    c_repo = SQLiteCredentialRepository(uow.connection)
    cfg = SecurityBaselineConfig(max_failed_logins=3, lockout_duration_seconds=10)
    mgr = PrincipalManager(p_repo, c_repo, config=cfg)

    # 1. Create principal with password
    user = mgr.create_principal("tenant-1", "alice", PrincipalType.HUMAN, password="StrongPassword1!")
    assert user["username"] == "alice"

    # 2. Successful login
    auth_user = mgr.authenticate_human("tenant-1", "alice", "StrongPassword1!")
    assert auth_user["principal_id"] == user["principal_id"]

    # 3. Failed login increments counter
    with pytest.raises(AuthenticationFailedError):
        mgr.authenticate_human("tenant-1", "alice", "Wrong1")
    with pytest.raises(AuthenticationFailedError):
        mgr.authenticate_human("tenant-1", "alice", "Wrong2")

    # 4. Third failed login triggers lockout
    with pytest.raises(PrincipalLockedError):
        mgr.authenticate_human("tenant-1", "alice", "Wrong3")

    # 5. Subsequent attempts during lockout immediately fail with PrincipalLockedError
    with pytest.raises(PrincipalLockedError):
        mgr.authenticate_human("tenant-1", "alice", "StrongPassword1!")

    # 6. Deactivated principal fails with PrincipalDisabledError
    mgr.disable_principal("tenant-1", user["principal_id"])
    with pytest.raises(PrincipalDisabledError):
        mgr.authenticate_human("tenant-1", "alice", "StrongPassword1!")


def test_session_lifecycle_and_timeouts(uow):
    p_repo = SQLitePrincipalRepository(uow.connection)
    c_repo = SQLiteCredentialRepository(uow.connection)
    s_repo = SQLiteSessionRepository(uow.connection)
    cfg = SecurityBaselineConfig(session_absolute_timeout_seconds=3600, session_idle_timeout_seconds=60)
    p_mgr = PrincipalManager(p_repo, c_repo, config=cfg)
    s_mgr = SessionManager(s_repo, p_repo, config=cfg)

    user = p_mgr.create_principal("tenant-1", "bob", PrincipalType.HUMAN, password="BobPassword123!")
    sess_id, raw_token = s_mgr.create_session("tenant-1", user["principal_id"])

    # 1. Valid validation
    sess = s_mgr.validate_session("tenant-1", sess_id, raw_token)
    assert sess["session_id"] == sess_id

    # 2. Revoked session
    s_mgr.revoke_session("tenant-1", sess_id, "TEST_REVOCATION")
    with pytest.raises(SessionRevokedError):
        s_mgr.validate_session("tenant-1", sess_id, raw_token)

    # 3. Security revision advancement invalidates old sessions
    sess_id2, raw_token2 = s_mgr.create_session("tenant-1", user["principal_id"])
    p_mgr.set_password("tenant-1", user["principal_id"], "NewPasswordBob123!")
    with pytest.raises(SessionSecurityRevisionMismatchError):
        s_mgr.validate_session("tenant-1", sess_id2, raw_token2)


def test_service_api_tokens(uow):
    p_repo = SQLitePrincipalRepository(uow.connection)
    t_repo = SQLiteServiceTokenRepository(uow.connection)
    p_mgr = PrincipalManager(p_repo, SQLiteCredentialRepository(uow.connection))
    t_auth = ServiceTokenAuthority(t_repo, p_repo)

    svc_user = p_mgr.create_principal("tenant-1", "svc-worker", PrincipalType.SERVICE)
    tok_id, raw_token = t_auth.issue_token("tenant-1", svc_user["principal_id"], "ci-token", ["migration.create", "migration.start"])

    # Validate token
    res = t_auth.validate_token(raw_token)
    assert res["principal_id"] == svc_user["principal_id"]
    assert "migration.create" in res["scopes"]

    # Revoke token
    t_auth.revoke_token("tenant-1", tok_id)
    with pytest.raises(ServiceTokenRevokedError):
        t_auth.validate_token(raw_token)


def test_flat_groups_and_nested_group_prohibition(uow):
    p_repo = SQLitePrincipalRepository(uow.connection)
    g_repo = SQLiteGroupRepository(uow.connection)
    p_mgr = PrincipalManager(p_repo, SQLiteCredentialRepository(uow.connection))
    g_auth = GroupAuthority(g_repo, p_repo)

    u1 = p_mgr.create_principal("tenant-1", "user1", PrincipalType.HUMAN)
    g1 = g_auth.create_group("tenant-1", "DevOpsEngineers")

    # Add member to flat group
    g_auth.add_member("tenant-1", g1, u1["principal_id"], "admin-system")
    groups = g_auth.get_principal_groups("tenant-1", u1["principal_id"])
    assert g1 in groups

    # Attempting to add a nested group ID as member raises NestedGroupsNotSupportedError
    with pytest.raises(NestedGroupsNotSupportedError):
        g_auth.add_member("tenant-1", g1, "grp-nested-01", "admin-system")
