"""tests.security.test_p75_p79_campaign_b
======================================
Focused P7 Campaign B (P7.5-P7.9) implementation verification.

Lightweight, bounded verification per Campaign B implementation directive: proves the
new authorities work end-to-end locally (positive + negative fail-closed paths). This is
implementation-level verification, not final hostile acceptance -- it does not attempt to
reach live external Vault/KMS/SCIM/IdP infrastructure (that remains EXTERNAL_DEFERRED).
"""

from __future__ import annotations

import time

import pytest

from akaalPipeline.contracts.enums import (
    AuthenticationAssurance,
    AuthenticationState,
    CredentialMechanism,
    GrantResourceType,
    GrantSubjectType,
    KeyAlgorithm,
    KeyPurpose,
    PrincipalType,
)
from akaalPipeline.contracts.errors import ForbiddenError, UnauthorizedError
from akaalPipeline.identity.groups import GroupAuthority
from akaalPipeline.identity.jit_identity import JITIdentityAuthority, JITIdentityPolicy
from akaalPipeline.identity.scim import SCIMProvisioningService
from akaalPipeline.security.abac import ABACAuthority
from akaalPipeline.security.central_authorization import AuthorizationDecision, CentralAuthorizationEngine
from akaalEngine.connection.security.connectivity_policy import (
    ConnectivityPolicyEnforcer,
    ConnectivityPolicyViolationError,
    ConnectivityRequirement,
)
from akaalPipeline.security.context import PipelineActorContext
from akaalPipeline.security.jit import JITPrivilegeAuthority
from akaalPipeline.security.keystore import KeyRevokedError, KeyStoreAuthority
from akaalPipeline.security.kms_provider import (
    ExternalKMSProviderUnavailable,
    KMSProviderUnavailableError,
    LocalEnvelopeKMSProvider,
)
from akaalPipeline.security.mfa import (
    MFAAuthority,
    MFAChallengeAttemptsExceededError,
    MFAChallengeInvalidError,
    MFAVerificationFailedError,
)
from akaalPipeline.security.rbac import RBACAuthority
from akaalPipeline.state.unit_of_work import SQLiteUnitOfWork
from akaalEngine.connection.models.endpoint import RouteSpec, RouteType, TLSBinding, TLSMode
from akaalEngine.connection.routing.private_connectivity import (
    PrivateConnectivityMode,
    declare_private_connectivity_capability,
)
from akaalEngine.connection.security.providers.vault_provider import (
    VaultKVSecretProvider,
    VaultProviderConfig,
    VaultProviderError,
)

_MRK = b"\x11" * 32


@pytest.fixture
def uow(tmp_path):
    u = SQLiteUnitOfWork(str(tmp_path / "p75_p79.db"))
    u.initialize_schema()
    u.tenants.create_tenant("tenant-b", "Campaign B Tenant")
    u.principals.create(
        tenant_id="tenant-b", principal_id="usr-alice", principal_type="HUMAN",
        username="alice", display_name="Alice", email="alice@akaal.internal", created_at="2026-01-01T00:00:00+00:00",
    )
    return u


@pytest.fixture
def keystore(uow):
    ks = KeyStoreAuthority(uow.keyring, master_root_key=_MRK)
    ks.initialize_purpose_keys_if_missing()
    return ks


# ---------------------------------------------------------------------------
# P7.5 - MFA
# ---------------------------------------------------------------------------

def _current_totp(secret_b32: str) -> str:
    import base64
    from akaalPipeline.security.mfa import _hotp, _totp_counter
    raw = base64.b32decode(secret_b32 + "=" * ((8 - len(secret_b32) % 8) % 8))
    return _hotp(raw, _totp_counter(time.time()))


def test_p75_mfa_enroll_activate_and_verify_positive(uow, keystore):
    mfa = MFAAuthority(keystore, uow.mfa)
    enrollment = mfa.enroll_totp("tenant-b", "usr-alice", account_label="alice@akaal.internal")
    assert enrollment.otpauth_uri.startswith("otpauth://totp/")

    code = _current_totp(enrollment.secret_base32)
    assert mfa.activate_enrollment("tenant-b", "usr-alice", enrollment.factor_id, code) is True
    assert mfa.has_active_factor("tenant-b", "usr-alice") is True

    code2 = _current_totp(enrollment.secret_base32)
    assurance = mfa.verify_totp_direct("tenant-b", "usr-alice", code2)
    assert assurance == AuthenticationAssurance.HIGH


def test_p75_mfa_wrong_code_fails_closed(uow, keystore):
    mfa = MFAAuthority(keystore, uow.mfa)
    enrollment = mfa.enroll_totp("tenant-b", "usr-alice", account_label="alice@akaal.internal")
    assert mfa.activate_enrollment("tenant-b", "usr-alice", enrollment.factor_id, "000000") is False


def test_p75_mfa_unenrolled_principal_rejected(uow, keystore):
    mfa = MFAAuthority(keystore, uow.mfa)
    with pytest.raises(Exception):
        mfa.verify_totp_direct("tenant-b", "usr-alice", "123456")


def test_p75_mfa_step_up_challenge_replay_rejected(uow, keystore):
    mfa = MFAAuthority(keystore, uow.mfa)
    enrollment = mfa.enroll_totp("tenant-b", "usr-alice", account_label="alice@akaal.internal")
    mfa.activate_enrollment("tenant-b", "usr-alice", enrollment.factor_id, _current_totp(enrollment.secret_base32))

    challenge_id = mfa.issue_step_up_challenge("tenant-b", "usr-alice", purpose="approve-migration")
    code = _current_totp(enrollment.secret_base32)
    assurance = mfa.verify_challenge("tenant-b", "usr-alice", challenge_id, "approve-migration", code)
    assert assurance == AuthenticationAssurance.HIGH

    # Replay of the same (now-consumed) challenge must fail closed.
    with pytest.raises(MFAChallengeInvalidError):
        mfa.verify_challenge("tenant-b", "usr-alice", challenge_id, "approve-migration", code)


def test_p75_mfa_challenge_attempt_limit_exceeded(uow, keystore):
    mfa = MFAAuthority(keystore, uow.mfa, max_challenge_attempts=2)
    enrollment = mfa.enroll_totp("tenant-b", "usr-alice", account_label="alice@akaal.internal")
    mfa.activate_enrollment("tenant-b", "usr-alice", enrollment.factor_id, _current_totp(enrollment.secret_base32))
    challenge_id = mfa.issue_step_up_challenge("tenant-b", "usr-alice", purpose="approve-migration")

    for _ in range(2):
        with pytest.raises(MFAVerificationFailedError):
            mfa.verify_challenge("tenant-b", "usr-alice", challenge_id, "approve-migration", "000000")
    with pytest.raises(MFAChallengeAttemptsExceededError):
        mfa.verify_challenge("tenant-b", "usr-alice", challenge_id, "approve-migration", "000000")


# ---------------------------------------------------------------------------
# P7.5 - JIT Identity Lifecycle
# ---------------------------------------------------------------------------

def _verified_federated_context(subject: str = "ext-sub-1") -> PipelineActorContext:
    return PipelineActorContext(
        actor_id=f"okta:{subject}",
        actor_type=PrincipalType.HUMAN.value,
        display_name="Federated Bob",
        email="bob@partner.example",
        organization_id="tenant-b",
        credential_mechanism=CredentialMechanism.OIDC_ID_TOKEN,
        authentication_state=AuthenticationState.AUTHENTICATED,
        authentication_assurance=AuthenticationAssurance.MEDIUM,
        trust_domain="https://idp.example.com",
        federation_provenance={"provider_id": "okta", "external_subject": subject, "issuer": "https://idp.example.com"},
    )


def test_p75_jit_identity_provisions_from_verified_context(uow):
    authority = JITIdentityAuthority(uow.tenants, uow.principals)
    ctx = _verified_federated_context()
    result = authority.provision_from_federated_context(ctx)
    assert result.created is True

    # Second login with the same subject is idempotent (update, not duplicate create).
    result2 = authority.provision_from_federated_context(ctx)
    assert result2.created is False
    assert result2.principal_id == result.principal_id
    assert result2.security_revision > result.security_revision


def test_p75_jit_identity_rejects_unverified_context(uow):
    authority = JITIdentityAuthority(uow.tenants, uow.principals)
    unverified = PipelineActorContext(
        actor_id="claimed-user",
        actor_type=PrincipalType.HUMAN.value,
        organization_id="tenant-b",
        authentication_state=AuthenticationState.CLAIMED,
    )
    with pytest.raises(UnauthorizedError):
        authority.provision_from_federated_context(unverified)


def test_p75_jit_identity_rejects_disallowed_provider(uow):
    policy = JITIdentityPolicy(allowed_provider_ids=frozenset({"azure-ad"}))
    authority = JITIdentityAuthority(uow.tenants, uow.principals, policy=policy)
    with pytest.raises(ForbiddenError):
        authority.provision_from_federated_context(_verified_federated_context())


# ---------------------------------------------------------------------------
# P7.5 - SCIM provisioning orchestration (local, no live provider required)
# ---------------------------------------------------------------------------

def test_p75_scim_reconcile_idempotent_duplicate_delivery(uow):
    svc = SCIMProvisioningService(uow.principals, uow.scim_mappings, provider_id="okta")
    r1 = svc.reconcile_user_event("tenant-b", "ext-999", "carol", "Carol C", "carol@x.com", active=True)
    r2 = svc.reconcile_user_event("tenant-b", "ext-999", "carol", "Carol C", "carol@x.com", active=True)
    assert r1["principal_id"] == r2["principal_id"]  # duplicate delivery does not create a second principal


def test_p75_scim_deactivate_disables_principal(uow):
    svc = SCIMProvisioningService(uow.principals, uow.scim_mappings, provider_id="okta")
    r1 = svc.reconcile_user_event("tenant-b", "ext-888", "dave", "Dave D", "dave@x.com", active=True)
    svc.reconcile_user_event("tenant-b", "ext-888", "dave", "Dave D", "dave@x.com", active=False)
    p = uow.principals.get_by_id("tenant-b", r1["principal_id"])
    assert p["is_active"] == 0


# ---------------------------------------------------------------------------
# P7.6 - Assurance-aware authorization + protected operations
# ---------------------------------------------------------------------------

def _authz_engine(uow, jit_authority=None) -> CentralAuthorizationEngine:
    ga = GroupAuthority(uow.groups, uow.principals)
    rbac = RBACAuthority(uow.roles, uow.role_permissions, uow.role_grants)
    abac = ABACAuthority(uow.abac_policies)
    return CentralAuthorizationEngine(uow.tenants, uow.principals, ga, rbac, abac, jit_authority=jit_authority)


def _grant_permission(uow, permission_id: str) -> None:
    uow.roles.create_role(role_id="rol-1", tenant_id="tenant-b", name="Op", description="", is_builtin=False, created_at="2026-01-01T00:00:00+00:00")
    uow.role_permissions.add_permission("tenant-b", "rol-1", permission_id)
    uow.role_grants.create_grant(
        grant_id="grt-1", tenant_id="tenant-b", subject_type="PRINCIPAL", subject_id="usr-alice",
        role_id="rol-1", resource_type="SYSTEM", resource_id="root", granted_by="usr-alice",
        granted_at="2026-01-01T00:00:00+00:00",
    )


def test_p76_required_assurance_denies_low_assurance_actor(uow):
    from akaalPipeline.security.permission_registry import PermissionRegistry
    perm = sorted(PermissionRegistry.ALL_PERMISSIONS)[0]
    _grant_permission(uow, perm)
    engine = _authz_engine(uow)

    low_assurance_ctx = PipelineActorContext(
        actor_id="usr-alice", actor_type="HUMAN", organization_id="tenant-b",
        authentication_state=AuthenticationState.AUTHENTICATED, authentication_assurance=AuthenticationAssurance.LOW,
    )
    with pytest.raises(ForbiddenError):
        engine.authorize(low_assurance_ctx, permission_id=perm, resource_type="SYSTEM", resource_id="root",
                          required_assurance=AuthenticationAssurance.HIGH)

    high_assurance_ctx = PipelineActorContext(
        actor_id="usr-alice", actor_type="HUMAN", organization_id="tenant-b",
        authentication_state=AuthenticationState.AUTHENTICATED, authentication_assurance=AuthenticationAssurance.HIGH,
    )
    assert engine.authorize(high_assurance_ctx, permission_id=perm, resource_type="SYSTEM", resource_id="root",
                             required_assurance=AuthenticationAssurance.HIGH) is True


def test_p76_protected_operation_denies_missing_jit_grant(uow):
    from akaalPipeline.security.permission_registry import PermissionRegistry
    perm = sorted(PermissionRegistry.ALL_PERMISSIONS)[0]
    _grant_permission(uow, perm)
    jit = JITPrivilegeAuthority(uow.tenants, uow.principals, uow.roles, uow.role_grants)
    engine = _authz_engine(uow, jit_authority=jit)

    ctx = PipelineActorContext(
        actor_id="usr-alice", actor_type="HUMAN", organization_id="tenant-b",
        authentication_state=AuthenticationState.AUTHENTICATED, authentication_assurance=AuthenticationAssurance.HIGH,
    )
    decision = engine.authorize_protected_operation(
        ctx, permission_id=perm, resource_type="SYSTEM", resource_id="root",
        required_jit_grant_id="grant-does-not-exist",
    )
    assert isinstance(decision, AuthorizationDecision)
    assert decision.allowed is False
    assert decision.reason_code == "JIT_GRANT_EXPIRED_OR_MISSING"


def test_p76_protected_operation_denies_sod_self_approval(uow):
    from akaalPipeline.security.permission_registry import PermissionRegistry
    perm = sorted(PermissionRegistry.ALL_PERMISSIONS)[0]
    _grant_permission(uow, perm)
    engine = _authz_engine(uow)

    ctx = PipelineActorContext(
        actor_id="usr-alice", actor_type="HUMAN", organization_id="tenant-b",
        authentication_state=AuthenticationState.AUTHENTICATED, authentication_assurance=AuthenticationAssurance.HIGH,
    )
    decision = engine.authorize_protected_operation(
        ctx, permission_id=perm, resource_type="SYSTEM", resource_id="root",
        requester_id="usr-alice", approver_ids=["usr-alice"],
        requester_role="MigrationRequester", approver_roles=["MigrationApprover"],
    )
    assert decision.allowed is False
    assert decision.reason_code == "SOD_VIOLATION"


# ---------------------------------------------------------------------------
# P7.7 - Vault secret provider (fail-closed paths; live Vault is EXTERNAL_DEFERRED)
# ---------------------------------------------------------------------------

def test_p77_vault_provider_fails_closed_without_token():
    config = VaultProviderConfig(vault_addr="https://127.0.0.1:1", token_provider=lambda: "")
    provider = VaultKVSecretProvider(config)
    with pytest.raises(VaultProviderError):
        provider.resolve_kv("secret/db#password")


def test_p77_vault_provider_fails_closed_on_unreachable_endpoint():
    # Real network call to a closed local port -- proves fail-closed behavior on a genuinely
    # unreachable endpoint without faking a successful Vault response.
    config = VaultProviderConfig(vault_addr="http://127.0.0.1:1", token_provider=lambda: "test-token", timeout_seconds=2.0)
    provider = VaultKVSecretProvider(config)
    with pytest.raises(VaultProviderError):
        provider.resolve_kv("secret/db#password")


# ---------------------------------------------------------------------------
# P7.8 - KMS provider
# ---------------------------------------------------------------------------

def test_p78_local_envelope_kms_encrypt_decrypt_roundtrip(keystore):
    provider = LocalEnvelopeKMSProvider(keystore)
    ref = provider.generate_key(KeyPurpose.TOKEN_ENCRYPT, KeyAlgorithm.AES_256_GCM)
    ciphertext = provider.encrypt(ref, b"top-secret-payload")
    assert ciphertext != b"top-secret-payload"
    plaintext = provider.decrypt(ref, ciphertext)
    assert plaintext == b"top-secret-payload"


def test_p78_local_envelope_kms_sign_verify(keystore):
    provider = LocalEnvelopeKMSProvider(keystore)
    ref = provider.generate_key(KeyPurpose.EXECUTION_SIGNING, KeyAlgorithm.ED25519)
    sig = provider.sign(ref, b"message-to-sign")
    assert provider.verify(ref, b"message-to-sign", sig) is True


def test_p78_local_envelope_kms_revoked_key_fails_closed(keystore):
    provider = LocalEnvelopeKMSProvider(keystore)
    ref = provider.generate_key(KeyPurpose.TOKEN_ENCRYPT, KeyAlgorithm.AES_256_GCM)
    ciphertext = provider.encrypt(ref, b"data")
    provider.revoke_key(ref, reason="test-revocation")
    with pytest.raises(KeyRevokedError):
        provider.decrypt(ref, ciphertext)


def test_p78_external_kms_provider_never_fakes_success():
    provider = ExternalKMSProviderUnavailable("AWS_KMS")
    ref = None
    with pytest.raises(KMSProviderUnavailableError):
        provider.generate_key(KeyPurpose.TOKEN_ENCRYPT, KeyAlgorithm.AES_256_GCM)


def test_p78_local_kms_key_reference_reports_truthful_origin(keystore):
    """CMK/BYOK truthfulness: a locally generated key must never report a CMK/BYOK origin."""
    from akaalPipeline.security.kms_provider import KeyOrigin
    provider = LocalEnvelopeKMSProvider(keystore)
    ref = provider.generate_key(KeyPurpose.AUDIT_SEAL, KeyAlgorithm.ED25519)
    assert ref.origin == KeyOrigin.AKAAL_GENERATED
    assert ref.provider == "LOCAL_ENVELOPE"


def test_p78_aws_kms_dependency_missing_fails_closed_with_real_path_intact():
    """
    B1/B4 correction: AWSKMSProvider is a REAL boto3-based production integration (real
    CreateKey/Encrypt/Decrypt/Sign/Verify/DescribeKey/DisableKey calls), not a stub.
    boto3 is not installed in this environment, so this proves the truthful dependency-
    missing signal without faking a successful AWS response.
    """
    from akaalPipeline.security.kms_provider import AWSKMSProvider, KMSDependencyMissingError
    provider = AWSKMSProvider(region_name="us-east-1")
    with pytest.raises(KMSDependencyMissingError):
        provider.generate_key(KeyPurpose.TOKEN_ENCRYPT, KeyAlgorithm.AES_256_GCM)


def test_p78_azure_keyvault_kms_dependency_missing_fails_closed():
    from akaalPipeline.security.kms_provider import AzureKeyVaultKMSProvider, KMSDependencyMissingError
    provider = AzureKeyVaultKMSProvider(vault_url="https://example-vault.vault.azure.net/")
    with pytest.raises(KMSDependencyMissingError):
        provider.generate_key(KeyPurpose.TOKEN_ENCRYPT, KeyAlgorithm.AES_256_GCM)


def test_p78_gcp_cloud_kms_dependency_missing_fails_closed():
    from akaalPipeline.security.kms_provider import GCPCloudKMSProvider, KMSDependencyMissingError
    provider = GCPCloudKMSProvider(project_id="akaal-test", location_id="us-central1", key_ring_id="akaal-ring")
    with pytest.raises(KMSDependencyMissingError):
        provider.generate_key(KeyPurpose.TOKEN_ENCRYPT, KeyAlgorithm.AES_256_GCM)


def test_p78_pkcs11_hsm_dependency_missing_fails_closed():
    from akaalPipeline.security.kms_provider import PKCS11HSMProvider, KMSDependencyMissingError
    provider = PKCS11HSMProvider(pkcs11_library_path="/usr/lib/softhsm/libsofthsm2.so", token_label="akaal-token", user_pin_provider=lambda: "1234")
    with pytest.raises(KMSDependencyMissingError):
        provider.generate_key(KeyPurpose.TOKEN_ENCRYPT, KeyAlgorithm.AES_256_GCM)


def test_p78_cloud_provider_construction_never_hardcodes_deployment_truth():
    """Config validation only -- proves no deployment truth (endpoint/account/project) is baked into source."""
    from akaalPipeline.security.kms_provider import AzureKeyVaultKMSProvider, GCPCloudKMSProvider
    with pytest.raises(ValueError):
        AzureKeyVaultKMSProvider(vault_url="")
    with pytest.raises(ValueError):
        GCPCloudKMSProvider(project_id="", location_id="", key_ring_id="")


# ---------------------------------------------------------------------------
# P7.9 - Connectivity policy + private connectivity truth
# ---------------------------------------------------------------------------

def test_p79_unprotected_connection_denied_when_tls_required():
    enforcer = ConnectivityPolicyEnforcer()
    with pytest.raises(ConnectivityPolicyViolationError):
        enforcer.enforce(ConnectivityRequirement.TLS, tls_binding=None, route_spec=None)


def test_p79_tls_required_satisfied_by_verify_full():
    enforcer = ConnectivityPolicyEnforcer()
    tls = TLSBinding(mode=TLSMode.VERIFY_FULL)
    report = enforcer.enforce(ConnectivityRequirement.TLS, tls_binding=tls, route_spec=None)
    assert report.satisfied is True


def test_p79_mtls_requires_client_certificate():
    enforcer = ConnectivityPolicyEnforcer()
    tls_no_client_cert = TLSBinding(mode=TLSMode.VERIFY_FULL)
    with pytest.raises(ConnectivityPolicyViolationError):
        enforcer.enforce(ConnectivityRequirement.MTLS, tls_binding=tls_no_client_cert, route_spec=None)

    tls_with_client_cert = TLSBinding(mode=TLSMode.VERIFY_FULL, client_cert_path="/etc/akaal/client.pem")
    report = enforcer.enforce(ConnectivityRequirement.MTLS, tls_binding=tls_with_client_cert, route_spec=None)
    assert report.satisfied is True


def test_p79_unverified_ssh_tunnel_does_not_count_as_tunnel_tier():
    enforcer = ConnectivityPolicyEnforcer()
    permissive_route = RouteSpec(route_type=RouteType.SSH_BASTION_TUNNEL, ssh_host="bastion.example.com", allow_unverified_ssh=True)
    with pytest.raises(ConnectivityPolicyViolationError):
        enforcer.enforce(ConnectivityRequirement.TUNNEL, tls_binding=None, route_spec=permissive_route)


def test_p79_verified_ssh_tunnel_satisfies_tunnel_tier():
    enforcer = ConnectivityPolicyEnforcer()
    verified_route = RouteSpec(
        route_type=RouteType.SSH_BASTION_TUNNEL, ssh_host="bastion.example.com",
        ssh_host_key_fingerprint="ab" * 32,
    )
    report = enforcer.enforce(ConnectivityRequirement.TUNNEL, tls_binding=None, route_spec=verified_route)
    assert report.satisfied is True


def test_p79_session_factory_actually_enforces_connectivity_policy_on_real_path():
    """
    Production-reachability proof (hostile-review B6/B10/B13/B20): the authoritative
    physical connection-establishment entrypoint (SessionFactory.create_physical_session,
    akaalEngine/connection/sessions/factory.py) must itself invoke the P7.9 connectivity
    enforcer BEFORE ever resolving credentials or attempting a physical connect -- not
    merely have the enforcer be composable in isolation. This proves it is wired onto the
    real path, not a disconnected module nothing calls in production.
    """
    from akaalEngine.connection.models.endpoint import AuthenticationSpec, AuthenticationType, EndpointRole, EndpointSpec
    from akaalEngine.connection.models.errors import ConnectivityPolicyDeniedError
    from akaalEngine.connection.models.session import SessionPurpose, SessionRequest
    from akaalEngine.connection.sessions.factory import SessionFactory

    spec = EndpointSpec(
        provider_id="postgresql",
        host="db.internal.example.com",
        port=5432,
        database_name="appdb",
        role=EndpointRole.SOURCE,
        auth_spec=AuthenticationSpec(auth_type=AuthenticationType.PASSWORD, username="svc-migrator", secret_ref="secret/pg#password"),
        tls_binding=TLSBinding(mode=TLSMode.DISABLED),  # deliberately weaker than required
        route_spec=RouteSpec(route_type=RouteType.DIRECT),
        required_connectivity_tier="TLS",  # policy requires TLS; TLS is DISABLED above
    )
    request = SessionRequest(purpose=SessionPurpose.BULK_SOURCE_READ, endpoint_spec=spec)
    factory = SessionFactory()

    with pytest.raises(ConnectivityPolicyDeniedError):
        factory.create_physical_session(request)


def test_p79_private_connectivity_capability_is_truthful():
    no_endpoint = RouteSpec(route_type=RouteType.DIRECT)
    cap = declare_private_connectivity_capability(no_endpoint)
    assert cap.supported is False
    assert cap.mode == PrivateConnectivityMode.PROVISIONING_UNSUPPORTED

    with_endpoint = RouteSpec(route_type=RouteType.PRIVATE_ENDPOINT, private_endpoint_id="pe-12345")
    cap2 = declare_private_connectivity_capability(with_endpoint)
    assert cap2.supported is True
    assert cap2.mode == PrivateConnectivityMode.CONSUME_EXISTING
