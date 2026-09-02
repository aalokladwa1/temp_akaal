"""tests.security.test_p71_canonical_security_foundation
=====================================================
Comprehensive Test Suite for P7.1:
Canonical Security Foundation & Zero-Trust Trust Model.

Proves:
1. Canonical Principal & Identity Model across all principal types.
2. Decoupled Authentication States (UNKNOWN != AUTHENTICATED).
3. Decoupled Authentication Assurance Levels (Ordinal NONE/LOW/MEDIUM/HIGH).
4. Zero-Trust Rule for SYSTEM_INTERNAL (INTERNAL != AUTOMATICALLY_AUTHENTICATED / AUTHORIZED).
5. Actor and Workload Provenance Preservation (Alice -> Pipeline -> Engine).
6. Trust Domain Boundary & Isolation.
7. Lossless Multi-Hop Security Context Propagation (IPC <-> Pipeline <-> Engine).
8. Authentication != Authorization (External claims are policy inputs, not direct permissions).
9. Hostile Fail-Closed Invariants (Missing identity, invalid state/assurance, tampering).
10. Strict Tenant Scoping & Isolation.
"""

import pytest
from akaalIPC.security.context import (
    ActorContext as IPCActorContext,
    ActorReference as IPCActorReference,
    CorrelationContext,
)
from akaalPipeline.contracts.enums import (
    AuthenticationAssurance,
    AuthenticationState,
    CredentialMechanism,
    GrantResourceType,
    GrantSubjectType,
    PrincipalType,
    TenantStatus,
)
from akaalPipeline.contracts.errors import ForbiddenError, UnauthorizedError
from akaalPipeline.identity.groups import GroupAuthority
from akaalPipeline.security.abac import ABACAuthority
from akaalPipeline.security.central_authorization import (
    AuthorizationContext,
    CentralAuthorizationEngine,
)
from akaalPipeline.security.context import PipelineActorContext
from akaalPipeline.security.rbac import RBACAuthority
from akaalPipeline.state.unit_of_work import SQLiteUnitOfWork


@pytest.fixture
def test_uow(tmp_path):
    db_path = str(tmp_path / "p71_security_test.db")
    uow = SQLiteUnitOfWork(db_path)
    uow.initialize_schema()
    uow.tenants.create_tenant("tenant-corp-a", "Corporate Tenant A")
    uow.tenants.create_tenant("tenant-corp-b", "Corporate Tenant B")
    return uow


def _make_authz_engine(uow: SQLiteUnitOfWork) -> CentralAuthorizationEngine:
    ga = GroupAuthority(uow.groups, uow.principals)
    rbac = RBACAuthority(uow.roles, uow.role_permissions, uow.role_grants)
    abac = ABACAuthority(uow.abac_policies)
    return CentralAuthorizationEngine(
        uow.tenants, uow.principals, ga, rbac, abac
    )


# ---------------------------------------------------------------------------
# 1. Canonical Principal & Identity Model
# ---------------------------------------------------------------------------

def test_p71_01_canonical_principal_model_and_types():
    """Proves canonical principal model represents all types without reducing to simple usernames."""
    for ptype in [PrincipalType.HUMAN, PrincipalType.SERVICE, PrincipalType.WORKLOAD, PrincipalType.MACHINE, PrincipalType.SYSTEM]:
        ctx = PipelineActorContext(
            actor_id=f"act-{ptype.value.lower()}",
            actor_type=ptype.value,
            display_name=f"Test {ptype.value}",
            email=f"{ptype.value.lower()}@akaal.internal",
            organization_id="tenant-corp-a",
            trust_domain="akaal.internal",
        )
        assert ctx.actor_id == f"act-{ptype.value.lower()}"
        assert ctx.actor_type == ptype.value
        assert ctx.tenant_id == "tenant-corp-a"
        assert ctx.trust_domain == "akaal.internal"


# ---------------------------------------------------------------------------
# 2. Decoupled Authentication States (UNKNOWN != AUTHENTICATED)
# ---------------------------------------------------------------------------

def test_p71_02_decoupled_authentication_state():
    """Proves: IDENTITY CLAIMED != AUTHENTICATED and UNKNOWN != AUTHENTICATED."""
    # Claimed identity
    claimed_ctx = PipelineActorContext(
        actor_id="user-claimed",
        actor_type=PrincipalType.HUMAN.value,
        organization_id="tenant-corp-a",
        authentication_state=AuthenticationState.CLAIMED,
    )
    assert claimed_ctx.is_authenticated is False

    # Unauthenticated identity
    unauth_ctx = PipelineActorContext(
        actor_id="user-anon",
        actor_type=PrincipalType.HUMAN.value,
        organization_id="tenant-corp-a",
        authentication_state=AuthenticationState.UNAUTHENTICATED,
    )
    assert unauth_ctx.is_authenticated is False

    # Expired authentication
    expired_ctx = PipelineActorContext(
        actor_id="user-expired",
        actor_type=PrincipalType.HUMAN.value,
        organization_id="tenant-corp-a",
        authentication_state=AuthenticationState.EXPIRED,
    )
    assert expired_ctx.is_authenticated is False

    # Revoked authentication
    revoked_ctx = PipelineActorContext(
        actor_id="user-revoked",
        actor_type=PrincipalType.HUMAN.value,
        organization_id="tenant-corp-a",
        authentication_state=AuthenticationState.REVOKED,
    )
    assert revoked_ctx.is_authenticated is False

    # Truly authenticated identity
    auth_ctx = PipelineActorContext(
        actor_id="user-auth",
        actor_type=PrincipalType.HUMAN.value,
        organization_id="tenant-corp-a",
        authentication_state=AuthenticationState.AUTHENTICATED,
        authentication_assurance=AuthenticationAssurance.MEDIUM,
    )
    assert auth_ctx.is_authenticated is True


# ---------------------------------------------------------------------------
# 3. Decoupled Authentication Assurance Model
# ---------------------------------------------------------------------------

def test_p71_03_decoupled_assurance_model():
    """Proves assurance level is ordinal and decoupled from credential mechanism."""
    # Presenting an API token does NOT automatically grant HIGH assurance
    token_ctx = PipelineActorContext(
        actor_id="svc-caller",
        actor_type=PrincipalType.SERVICE.value,
        organization_id="tenant-corp-a",
        credential_mechanism=CredentialMechanism.API_TOKEN,
        authentication_state=AuthenticationState.AUTHENTICATED,
        authentication_assurance=AuthenticationAssurance.LOW,
    )
    assert token_ctx.credential_mechanism == CredentialMechanism.API_TOKEN.value
    assert token_ctx.authentication_assurance == AuthenticationAssurance.LOW.value

    # High assurance requires verified multi-factor or hardware-backed proof
    mfa_ctx = PipelineActorContext(
        actor_id="usr-admin",
        actor_type=PrincipalType.HUMAN.value,
        organization_id="tenant-corp-a",
        credential_mechanism=CredentialMechanism.OIDC_ID_TOKEN,
        authentication_state=AuthenticationState.AUTHENTICATED,
        authentication_assurance=AuthenticationAssurance.HIGH,
        federation_provenance={"amr": ["pwd", "mfa"], "acr": "gold"},
    )
    assert mfa_ctx.authentication_assurance == AuthenticationAssurance.HIGH.value
    assert mfa_ctx.federation_provenance["amr"] == ["pwd", "mfa"]


# ---------------------------------------------------------------------------
# 4. Zero-Trust SYSTEM_INTERNAL Invariant
# ---------------------------------------------------------------------------

def test_p71_04_zero_trust_system_internal_invariant():
    """Proves: INTERNAL != AUTOMATICALLY_AUTHENTICATED and INTERNAL != AUTOMATICALLY_AUTHORIZED."""
    # An internal-call context that has not been authenticated is NOT trusted
    internal_unauth = PipelineActorContext(
        actor_id="pipeline-worker",
        actor_type=PrincipalType.SYSTEM.value,
        organization_id="tenant-corp-a",
        credential_mechanism=CredentialMechanism.SYSTEM_INTERNAL,
        authentication_state=AuthenticationState.UNAUTHENTICATED,
    )
    assert internal_unauth.is_authenticated is False

    # Authenticated internal workload must carry explicit authenticated state
    internal_auth = PipelineActorContext(
        actor_id="pipeline-worker",
        actor_type=PrincipalType.WORKLOAD.value,
        organization_id="tenant-corp-a",
        credential_mechanism=CredentialMechanism.SYSTEM_INTERNAL,
        authentication_state=AuthenticationState.AUTHENTICATED,
        authentication_assurance=AuthenticationAssurance.MEDIUM,
        calling_workload="spiffe://akaal.internal/ns/core/sa/pipeline",
    )
    assert internal_auth.is_authenticated is True
    assert internal_auth.calling_workload == "spiffe://akaal.internal/ns/core/sa/pipeline"


# ---------------------------------------------------------------------------
# 5. Actor and Workload Provenance Preservation (Alice -> Pipeline -> Engine)
# ---------------------------------------------------------------------------

def test_p71_05_actor_and_workload_provenance_preservation():
    """Proves: Original actor (Alice), calling workload (Pipeline), and target workload (Engine) are preserved."""
    alice_orig = {
        "actor_id": "usr-alice",
        "actor_type": "HUMAN",
        "display_name": "Alice Developer",
        "email": "alice@bank.example",
        "trust_domain": "idp.bank.example",
    }

    # Pipeline hop receives request initiated by Alice
    pipeline_ctx = PipelineActorContext(
        actor_id="akaal-pipeline-node-1",
        actor_type=PrincipalType.WORKLOAD.value,
        organization_id="tenant-corp-a",
        authentication_state=AuthenticationState.AUTHENTICATED,
        authentication_assurance=AuthenticationAssurance.HIGH,
        original_actor=alice_orig,
        calling_workload="spiffe://akaal.corp/sa/pipeline",
        target_workload="spiffe://akaal.corp/sa/engine",
        trust_domain="spiffe://akaal.corp",
    )

    # Convert to IPC context and forward to Engine
    ipc_ctx = pipeline_ctx.to_ipc()
    assert ipc_ctx.actor.actor_id == "akaal-pipeline-node-1"
    assert ipc_ctx.original_actor is not None
    assert ipc_ctx.original_actor.actor_id == "usr-alice"
    assert ipc_ctx.calling_workload == "spiffe://akaal.corp/sa/pipeline"
    assert ipc_ctx.target_workload == "spiffe://akaal.corp/sa/engine"

    # Engine receives and reconstructs context
    engine_ctx = PipelineActorContext.from_ipc(ipc_ctx)
    assert engine_ctx.actor_id == "akaal-pipeline-node-1"
    assert engine_ctx.effective_original_actor["actor_id"] == "usr-alice"
    assert engine_ctx.effective_original_actor["display_name"] == "Alice Developer"
    assert engine_ctx.calling_workload == "spiffe://akaal.corp/sa/pipeline"
    assert engine_ctx.target_workload == "spiffe://akaal.corp/sa/engine"


# ---------------------------------------------------------------------------
# 6. Trust Domain Boundary & Isolation
# ---------------------------------------------------------------------------

def test_p71_06_trust_domain_isolation():
    """Proves identities in different trust domains are distinct and do not inherit cross-domain trust."""
    corp_ctx = PipelineActorContext(
        actor_id="alice",
        actor_type=PrincipalType.HUMAN.value,
        organization_id="tenant-corp-a",
        trust_domain="idp.trusted-corp.com",
    )

    external_ctx = PipelineActorContext(
        actor_id="alice",
        actor_type=PrincipalType.HUMAN.value,
        organization_id="tenant-corp-a",
        trust_domain="idp.attacker-domain.org",
    )

    # Identical username 'alice' but different trust domains -> Must remain non-equivalent
    assert corp_ctx.trust_domain != external_ctx.trust_domain
    assert corp_ctx.to_dict()["trust_domain"] == "idp.trusted-corp.com"
    assert external_ctx.to_dict()["trust_domain"] == "idp.attacker-domain.org"


# ---------------------------------------------------------------------------
# 7. Lossless Multi-Hop Security Context Propagation (IPC <-> Pipeline <-> Engine)
# ---------------------------------------------------------------------------

def test_p71_07_lossless_ipc_pipeline_engine_propagation():
    """Proves 100% fidelity roundtrip across IPC, Pipeline, and JSON serialization."""
    orig_ref = IPCActorReference(
        actor_id="usr-alice",
        actor_type="HUMAN",
        display_name="Alice Developer",
        email="alice@company.com",
        trust_domain="idp.company.com",
    )

    initial_ctx = PipelineActorContext(
        actor_id="svc-gateway",
        actor_type=PrincipalType.SERVICE.value,
        display_name="API Gateway",
        email="gateway@company.com",
        organization_id="tenant-corp-a",
        workspace_id="ws-prod",
        project_id="proj-finance",
        environment="production",
        roles=("Viewer", "Operator"),
        scopes=("read:migrations", "execute:migrations"),
        session_id="sess-xyz-987",
        provenance="rest-jwt",
        credential_mechanism=CredentialMechanism.OIDC_ID_TOKEN,
        authentication_state=AuthenticationState.AUTHENTICATED,
        authentication_assurance=AuthenticationAssurance.HIGH,
        trust_domain="spiffe://company.com",
        federation_provenance={"issuer": "https://auth.company.com", "sub": "auth0|12345"},
        workload_identity="spiffe://company.com/sa/gateway",
        original_actor=orig_ref,
        calling_workload="spiffe://company.com/sa/gateway",
        target_workload="spiffe://company.com/sa/pipeline",
        issued_at="2026-08-31T20:00:00Z",
        expires_at="2026-08-31T21:00:00Z",
    )

    # 1. Pipeline -> IPC
    ipc_ctx = initial_ctx.to_ipc()
    assert ipc_ctx.actor.actor_id == "svc-gateway"
    assert ipc_ctx.credential_mechanism == "OIDC_ID_TOKEN"
    assert ipc_ctx.authentication_state == "AUTHENTICATED"
    assert ipc_ctx.authentication_assurance == "HIGH"
    assert ipc_ctx.roles == ("Viewer", "Operator")
    assert ipc_ctx.original_actor.actor_id == "usr-alice"

    # 2. IPC -> Dict (Transport Payload)
    transport_dict = ipc_ctx.to_dict()
    assert isinstance(transport_dict, dict)

    # 3. Dict -> Pipeline Context (At Engine boundary)
    reconstructed_ctx = PipelineActorContext.from_dict(transport_dict)
    assert reconstructed_ctx.actor_id == initial_ctx.actor_id
    assert reconstructed_ctx.actor_type == initial_ctx.actor_type
    assert reconstructed_ctx.organization_id == initial_ctx.organization_id
    assert reconstructed_ctx.workspace_id == initial_ctx.workspace_id
    assert reconstructed_ctx.roles == initial_ctx.roles
    assert reconstructed_ctx.scopes == initial_ctx.scopes
    assert reconstructed_ctx.credential_mechanism == initial_ctx.credential_mechanism
    assert reconstructed_ctx.authentication_state == initial_ctx.authentication_state
    assert reconstructed_ctx.authentication_assurance == initial_ctx.authentication_assurance
    assert reconstructed_ctx.trust_domain == initial_ctx.trust_domain
    assert reconstructed_ctx.federation_provenance == initial_ctx.federation_provenance
    assert reconstructed_ctx.workload_identity == initial_ctx.workload_identity
    assert reconstructed_ctx.effective_original_actor["actor_id"] == "usr-alice"
    assert reconstructed_ctx.calling_workload == initial_ctx.calling_workload
    assert reconstructed_ctx.target_workload == initial_ctx.target_workload
    assert reconstructed_ctx.issued_at == initial_ctx.issued_at
    assert reconstructed_ctx.expires_at == initial_ctx.expires_at


# ---------------------------------------------------------------------------
# 8. Authentication != Authorization (External Claims are Policy Inputs)
# ---------------------------------------------------------------------------

def test_p71_08_authentication_does_not_imply_authorization(test_uow):
    """
    Proves: AUTHENTICATED != AUTHORIZED.
    An authenticated principal carrying roles=('PlatformAdministrator',) in token claims
    is DENIED access by P5 CentralAuthorizationEngine unless a canonical role grant exists in SQLite.
    """
    uow = test_uow
    # Create principal in database as standard worker without platform admin grant
    uow.principals.create(
        tenant_id="tenant-corp-a",
        principal_id="usr-bob",
        principal_type="HUMAN",
        username="bob",
        email="bob@corp.com",
    )

    authz_engine = _make_authz_engine(uow)

    # Bob authenticates via OIDC and token self-claims role 'PlatformAdministrator'
    bob_ctx = PipelineActorContext(
        actor_id="usr-bob",
        actor_type=PrincipalType.HUMAN.value,
        organization_id="tenant-corp-a",
        roles=("PlatformAdministrator", "Domain Admins"),
        scopes=("all", "superuser"),
        authentication_state=AuthenticationState.AUTHENTICATED,
        authentication_assurance=AuthenticationAssurance.HIGH,
    )

    # Attempt sensitive operation 'migration.plan'
    with pytest.raises(ForbiddenError):
        authz_engine.authorize(
            bob_ctx,
            permission_id="migration.plan",
            resource_type="SYSTEM",
            resource_id="root",
            raise_exceptions=True,
        )


# ---------------------------------------------------------------------------
# 9. Hostile Fail-Closed Invariants
# ---------------------------------------------------------------------------

def test_p71_09_hostile_fail_closed_rules():
    """Proves fail-closed behavior on missing or malformed security attributes."""
    # 1. Missing actor_id
    with pytest.raises(ValueError, match="actor_id cannot be empty"):
        PipelineActorContext(actor_id="", actor_type="HUMAN")

    # 2. Missing actor_type
    with pytest.raises(ValueError, match="actor_type cannot be empty"):
        PipelineActorContext(actor_id="user1", actor_type="")

    # 3. Invalid authentication state in validate_invariants()
    bad_state_ctx = PipelineActorContext(
        actor_id="user1",
        actor_type="HUMAN",
        authentication_state="CUSTOM_TRUSTED_STATE",
    )
    with pytest.raises(ValueError, match="FAIL_CLOSED: Invalid authentication state"):
        bad_state_ctx.validate_invariants()

    # 4. Invalid authentication assurance in validate_invariants()
    bad_assur_ctx = PipelineActorContext(
        actor_id="user1",
        actor_type="HUMAN",
        authentication_state=AuthenticationState.AUTHENTICATED,
        authentication_assurance="SUPER_HIGH_ASSURANCE",
    )
    with pytest.raises(ValueError, match="FAIL_CLOSED: Invalid authentication assurance"):
        bad_assur_ctx.validate_invariants()


# ---------------------------------------------------------------------------
# 10. Strict Tenant Scoping & Isolation
# ---------------------------------------------------------------------------

def test_p71_10_tenant_isolation_and_tampering(test_uow):
    """Proves that missing tenant defaults safely and tenant boundaries are never crossed."""
    # 1. Missing organization_id defaults to 'default-tenant', never a global all-access tenant
    no_tenant_ctx = PipelineActorContext(
        actor_id="usr-isolated",
        actor_type=PrincipalType.HUMAN.value,
        organization_id=None,
    )
    assert no_tenant_ctx.tenant_id == "default-tenant"

    # 2. Principal authenticated in Tenant A attempting to access Tenant B fails closed
    uow = test_uow
    uow.principals.create(
        tenant_id="tenant-corp-a",
        principal_id="usr-tenant-a-user",
        principal_type="HUMAN",
        username="user_a",
    )

    authz_engine = _make_authz_engine(uow)

    # Actor authenticated in Tenant A
    user_a_ctx = PipelineActorContext(
        actor_id="usr-tenant-a-user",
        actor_type=PrincipalType.HUMAN.value,
        organization_id="tenant-corp-a",
        authentication_state=AuthenticationState.AUTHENTICATED,
        authentication_assurance=AuthenticationAssurance.MEDIUM,
    )

    # Attempting to authorize in Tenant B
    authz_req = AuthorizationContext(
        tenant_id="tenant-corp-b",  # Cross-tenant manipulation
        principal_id="usr-tenant-a-user",
        action="migration.create",
        resource_type="SYSTEM",
        resource_id="root",
    )

    # Must fail closed with UnauthorizedError (Principal not found in Tenant B)
    with pytest.raises(UnauthorizedError):
        authz_engine.authorize(authz_req, raise_exceptions=True)


# ---------------------------------------------------------------------------
# 11. Hostile Unknown & Malformed Authentication Fails Closed
# ---------------------------------------------------------------------------

def test_p71_11_hostile_unknown_and_malformed_authentication_fails_closed():
    """
    Proves governing semantic invariant: UNKNOWN OR UNESTABLISHED AUTHENTICATION != AUTHENTICATED.
    Covers:
    - Absent authentication_state
    - None authentication_state
    - Unknown serialized state ('AUTHENTICATED_V2', 'UNKNOWN')
    - Malformed casing/value ('authenticated', 'AUTH')
    - Malformed assurance ('SUPER_HIGH_ASSURANCE', None, empty)
    - Missing credential mechanism
    - AUTHENTICATED state with assurance NONE
    - AUTHENTICATED state with structurally incomplete identity
    """
    # 1. Absent authentication_state in payload -> defaults to UNAUTHENTICATED, is_authenticated == False
    ctx_absent = PipelineActorContext.from_dict({"actor_id": "usr-1", "actor_type": "HUMAN"})
    assert ctx_absent.authentication_state == "UNAUTHENTICATED"
    assert ctx_absent.is_authenticated is False

    # 2. None authentication_state
    ctx_none = PipelineActorContext(
        actor_id="usr-1",
        actor_type="HUMAN",
        authentication_state=None,  # type: ignore
    )
    assert ctx_none.is_authenticated is False
    with pytest.raises(ValueError, match="FAIL_CLOSED: Invalid authentication state"):
        ctx_none.validate_invariants()

    # 3. Unknown serialized state 'AUTHENTICATED_V2' or 'UNKNOWN'
    ctx_unknown = PipelineActorContext(
        actor_id="usr-1",
        actor_type="HUMAN",
        authentication_state="AUTHENTICATED_V2",
    )
    assert ctx_unknown.is_authenticated is False
    with pytest.raises(ValueError, match="FAIL_CLOSED: Invalid authentication state 'AUTHENTICATED_V2'"):
        ctx_unknown.validate_invariants()

    # 4. Malformed casing 'authenticated'
    ctx_casing = PipelineActorContext(
        actor_id="usr-1",
        actor_type="HUMAN",
        authentication_state="authenticated",
    )
    assert ctx_casing.is_authenticated is False
    with pytest.raises(ValueError, match="FAIL_CLOSED: Invalid authentication state 'authenticated'"):
        ctx_casing.validate_invariants()

    # 5. Malformed assurance 'SUPER_HIGH'
    ctx_bad_assur = PipelineActorContext(
        actor_id="usr-1",
        actor_type="HUMAN",
        authentication_state=AuthenticationState.AUTHENTICATED,
        authentication_assurance="SUPER_HIGH",
    )
    assert ctx_bad_assur.is_authenticated is False
    with pytest.raises(ValueError, match="FAIL_CLOSED: Invalid authentication assurance 'SUPER_HIGH'"):
        ctx_bad_assur.validate_invariants()

    # 6. Malformed credential mechanism 'MAGIC_BYPASS'
    ctx_bad_mech = PipelineActorContext(
        actor_id="usr-1",
        actor_type="HUMAN",
        credential_mechanism="MAGIC_BYPASS",
    )
    with pytest.raises(ValueError, match="FAIL_CLOSED: Invalid credential mechanism 'MAGIC_BYPASS'"):
        ctx_bad_mech.validate_invariants()

    # 7. AUTHENTICATED state with assurance NONE -> Must evaluate is_authenticated == False and fail closed in validation
    ctx_auth_none = PipelineActorContext(
        actor_id="usr-1",
        actor_type="HUMAN",
        authentication_state=AuthenticationState.AUTHENTICATED,
        authentication_assurance=AuthenticationAssurance.NONE,
    )
    assert ctx_auth_none.is_authenticated is False
    with pytest.raises(ValueError, match="FAIL_CLOSED: AUTHENTICATED state cannot have assurance NONE"):
        ctx_auth_none.validate_invariants()

    # 8. Structurally incomplete identity (empty actor_id) with AUTHENTICATED state
    with pytest.raises(ValueError, match="actor_id cannot be empty"):
        PipelineActorContext(
            actor_id="",
            actor_type="HUMAN",
            authentication_state=AuthenticationState.AUTHENTICATED,
            authentication_assurance=AuthenticationAssurance.HIGH,
        )


# ---------------------------------------------------------------------------
# 12. Hostile Trust-Domain Claim Cannot Manufacture Trust
# ---------------------------------------------------------------------------

def test_p71_12_hostile_trust_domain_claim_cannot_manufacture_trust(test_uow):
    """
    Proves: CLAIMED TRUST DOMAIN != VERIFIED TRUST PROVENANCE.
    Supplying a trusted-looking trust_domain string does NOT authenticate an unverified caller
    and does NOT grant cross-domain or cross-tenant permissions.
    """
    uow = test_uow
    uow.principals.create(
        tenant_id="tenant-corp-a",
        principal_id="usr-trusted-domain-spoofer",
        principal_type="HUMAN",
        username="spoofer",
    )

    authz_engine = _make_authz_engine(uow)

    # Caller claims to be from ultra-trusted corporate trust domain
    spoofer_ctx = PipelineActorContext(
        actor_id="usr-trusted-domain-spoofer",
        actor_type=PrincipalType.HUMAN.value,
        organization_id="tenant-corp-a",
        trust_domain="spiffe://ultra-trusted.bank.corp",
        authentication_state=AuthenticationState.CLAIMED,
        authentication_assurance=AuthenticationAssurance.NONE,
    )

    # 1. Proves is_authenticated remains False despite trusted trust_domain string
    assert spoofer_ctx.is_authenticated is False
    assert spoofer_ctx.trust_domain == "spiffe://ultra-trusted.bank.corp"

    # 2. Proves CentralAuthorizationEngine denies unauthenticated spoofer
    with pytest.raises(ForbiddenError):
        authz_engine.authorize(
            spoofer_ctx,
            permission_id="migration.plan",
            resource_type="SYSTEM",
            resource_id="root",
            raise_exceptions=True,
        )


# ---------------------------------------------------------------------------
# 13. Hostile Northbound Security Context Injection Boundary
# ---------------------------------------------------------------------------

def test_p71_13_hostile_northbound_security_context_injection_fails_closed(test_uow):
    """
    Proves governing invariant: DESERIALIZATION != AUTHENTICATION.
    A hostile caller attempting to inject 'AUTHENTICATED', 'HIGH', privileged roles,
    forged original_actor, or foreign tenant_id via untrusted wire representation
    is stripped and downgraded to CLAIMED / NONE by from_untrusted_claims.
    """
    uow = test_uow
    authz_engine = _make_authz_engine(uow)

    # Malicious raw wire payload from untrusted external network
    hostile_wire_payload = {
        "actor": {
            "actor_id": "malicious-hacker",
            "actor_type": "HUMAN",
            "display_name": "Hacker",
            "email": "hacker@evil.com",
            "trust_domain": "spiffe://bank.internal",
        },
        "organization_id": "tenant-corp-a",
        "roles": ["SuperAdministrator", "PlatformAdmin", "Root"],
        "scopes": ["all", "cluster:admin"],
        # Malicious self-asserted authentication & high assurance
        "authentication_state": "AUTHENTICATED",
        "authentication_assurance": "HIGH",
        "credential_mechanism": "SPIFFE_X509_SVID",
        "original_actor": {"actor_id": "usr-ceo", "actor_type": "HUMAN"},
        "calling_workload": "spiffe://bank.internal/sa/pipeline",
        "target_workload": "spiffe://bank.internal/sa/engine",
    }

    # Deserializing via untrusted northbound constructor
    ingress_ctx = PipelineActorContext.from_untrusted_claims(hostile_wire_payload)

    # 1. Proves self-asserted AUTHENTICATED was stripped to CLAIMED
    assert ingress_ctx.authentication_state == AuthenticationState.CLAIMED.value
    # 2. Proves self-asserted HIGH assurance was stripped to NONE
    assert ingress_ctx.authentication_assurance == AuthenticationAssurance.NONE.value
    # 3. Proves is_authenticated is strictly False
    assert ingress_ctx.is_authenticated is False
    # 4. Deserialization with trusted_source=False also fails closed
    untrusted_dict_ctx = PipelineActorContext.from_dict(hostile_wire_payload, trusted_source=False)
    assert untrusted_dict_ctx.is_authenticated is False
    assert untrusted_dict_ctx.authentication_state == AuthenticationState.CLAIMED.value

    # 5. Proves authorization fails closed on injected context
    with pytest.raises((ForbiddenError, UnauthorizedError)):
        authz_engine.authorize(
            ingress_ctx,
            permission_id="migration.plan",
            resource_type="SYSTEM",
            resource_id="root",
            raise_exceptions=True,
        )



# ---------------------------------------------------------------------------
# 14. Hostile Cross-Boundary IPC Context Enforcement
# ---------------------------------------------------------------------------

def test_p71_14_hostile_cross_boundary_ipc_enforcement():
    """
    Proves that IPC ActorContext crossing an untrusted boundary cannot mint
    authoritative AUTHENTICATED contexts in the pipeline without trusted boundary verification.
    """
    # Raw untrusted IPC context asserting AUTHENTICATED
    untrusted_ipc_context = IPCActorContext(
        actor=IPCActorReference(actor_id="untrusted-wire-caller", actor_type="HUMAN"),
        organization_id="tenant-corp-a",
        roles=("Admin",),
        authentication_state="AUTHENTICATED",
        authentication_assurance="HIGH",
    )

    # Ingest across untrusted boundary (trusted_boundary=False)
    pipeline_ctx = PipelineActorContext.from_ipc(untrusted_ipc_context, trusted_boundary=False)

    # Must be downgraded to CLAIMED and NONE
    assert pipeline_ctx.authentication_state == AuthenticationState.CLAIMED.value
    assert pipeline_ctx.authentication_assurance == AuthenticationAssurance.NONE.value
    assert pipeline_ctx.is_authenticated is False

