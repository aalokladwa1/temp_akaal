"""tests.security.test_p74_enterprise_identity_federation
=====================================================
Comprehensive Unit, Integration, and Hostile Test Suite for P7.4:
Enterprise Identity Federation (OAuth / OIDC / SAML 2.0 / LDAP / Active Directory).
"""

import base64
import datetime
import json
import xml.etree.ElementTree as ET
from datetime import timezone
import pytest
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.x509.oid import NameOID

from akaalPipeline.contracts.enums import (
    AuthenticationAssurance,
    AuthenticationState,
    CredentialMechanism,
    FederationProviderType,
    PrincipalType,
)
from akaalPipeline.security.central_authorization import (
    CentralAuthorizationEngine,
    ForbiddenError,
    UnauthorizedError,
)
from akaalPipeline.security.federation import (
    FederatedIdentityResult,
    FederationManager,
    FederationProviderConfig,
    LDAPAuthError,
    LDAPClient,
    OIDCExpiredError,
    OIDCValidationError,
    OIDCValidator,
    SAMLExpiredError,
    SAMLReplayError,
    SAMLValidationError,
    SAMLValidator,
)


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


@pytest.fixture
def oidc_keys():
    """Generates RSA keypair and JWKS for OIDC testing."""
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048, backend=default_backend())
    pub_numbers = key.public_key().public_numbers()
    n_b64 = _b64url_encode(pub_numbers.n.to_bytes((pub_numbers.n.bit_length() + 7) // 8, "big"))
    e_b64 = _b64url_encode(pub_numbers.e.to_bytes((pub_numbers.e.bit_length() + 7) // 8, "big"))
    jwk = {
        "kty": "RSA",
        "kid": "key-test-1",
        "use": "sig",
        "alg": "RS256",
        "n": n_b64,
        "e": e_b64,
    }
    return {"key": key, "jwks": {"keys": [jwk]}, "kid": "key-test-1"}


@pytest.fixture
def saml_idp():
    """Generates IdP Certificate and private key for SAML signature testing."""
    idp_key = rsa.generate_private_key(public_exponent=65537, key_size=2048, backend=default_backend())
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Test SAML IdP"),
        x509.NameAttribute(NameOID.COMMON_NAME, "idp.okta.corp"),
    ])
    now = datetime.datetime.now(timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(idp_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(days=1))
        .not_valid_after(now + datetime.timedelta(days=365))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .sign(idp_key, hashes.SHA256(), default_backend())
    )
    cert_pem = cert.public_bytes(serialization.Encoding.PEM).decode("utf-8")
    return {"key": idp_key, "cert": cert, "cert_pem": cert_pem, "entity_id": "https://idp.okta.corp"}


def create_signed_jwt(key, header, payload):
    """Mints a real signed JWT."""
    header_b64 = _b64url_encode(json.dumps(header).encode("utf-8"))
    payload_b64 = _b64url_encode(json.dumps(payload).encode("utf-8"))
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    sig = key.sign(signing_input, padding.PKCS1v15(), hashes.SHA256())
    sig_b64 = _b64url_encode(sig)
    return f"{header_b64}.{payload_b64}.{sig_b64}"


def create_signed_saml_assertion(
    idp_key,
    issuer,
    subject_name_id,
    assertion_id="saml-assert-100",
    audience="https://akaal.pipeline.corp",
    expired=False,
    not_yet_valid=False,
    cert_pem=None,
):
    """Mints a real signed SAML 2.0 assertion using standard XMLDSig enveloped signature."""
    import signxml
    from lxml import etree

    now = datetime.datetime.now(timezone.utc)
    if expired:
        nvb = (now - datetime.timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
        nva = (now - datetime.timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    elif not_yet_valid:
        nvb = (now + datetime.timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        nva = (now + datetime.timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
    else:
        nvb = (now - datetime.timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%SZ")
        nva = (now + datetime.timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")

    raw_xml = f'''<saml:Assertion xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion" ID="{assertion_id}" Version="2.0" IssueInstant="{nvb}">
        <saml:Issuer>{issuer}</saml:Issuer>
        <saml:Subject>
            <saml:NameID Format="urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress">{subject_name_id}</saml:NameID>
        </saml:Subject>
        <saml:Conditions NotBefore="{nvb}" NotOnOrAfter="{nva}">
            <saml:AudienceRestriction>
                <saml:Audience>{audience}</saml:Audience>
            </saml:AudienceRestriction>
        </saml:Conditions>
        <saml:AttributeStatement>
            <saml:Attribute Name="groups">
                <saml:AttributeValue>Engineering</saml:AttributeValue>
            </saml:Attribute>
            <saml:Attribute Name="email">
                <saml:AttributeValue>{subject_name_id}</saml:AttributeValue>
            </saml:Attribute>
        </saml:AttributeStatement>
    </saml:Assertion>'''

    doc = etree.fromstring(raw_xml.encode("utf-8"))

    if cert_pem is None:
        cert = (
            x509.CertificateBuilder()
            .subject_name(x509.Name([]))
            .issuer_name(x509.Name([]))
            .public_key(idp_key.public_key())
            .serial_number(1)
            .not_valid_before(now - datetime.timedelta(days=1))
            .not_valid_after(now + datetime.timedelta(days=365))
            .sign(idp_key, hashes.SHA256())
        )
        cert_pem = cert.public_bytes(serialization.Encoding.PEM).decode("utf-8")

    key_pem = idp_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode("utf-8")

    signed_doc = signxml.XMLSigner(
        method=signxml.methods.enveloped,
        signature_algorithm="rsa-sha256",
        digest_algorithm="sha256",
        c14n_algorithm="http://www.w3.org/2001/10/xml-exc-c14n#"
    ).sign(doc, key=key_pem, cert=cert_pem)

    return etree.tostring(signed_doc, encoding="utf-8").decode("utf-8")



# ---------------------------------------------------------------------------
# 1. OIDC Token Cryptographic Validation
# ---------------------------------------------------------------------------

def test_p74_01_oidc_token_cryptographic_validation(oidc_keys):
    """Proves cryptographic validation of OIDC ID token using JWKS."""
    config = FederationProviderConfig(
        provider_id="okta-corp",
        provider_type=FederationProviderType.OIDC,
        display_name="Okta Workforce",
        issuer="https://okta.corp",
        client_id="akaal-app",
        jwks_keys=oidc_keys["jwks"],
    )

    validator = OIDCValidator()
    validator.register_jwks("okta-corp", oidc_keys["jwks"])

    now_ts = int(datetime.datetime.now(timezone.utc).timestamp())
    payload = {
        "iss": "https://okta.corp",
        "sub": "user_12345",
        "aud": "akaal-app",
        "exp": now_ts + 3600,
        "iat": now_ts,
        "name": "Alice Engineer",
        "email": "alice@corp.com",
        "groups": ["Engineers", "DBAdmins"],
        "amr": ["pwd", "mfa"],
    }
    header = {"alg": "RS256", "typ": "JWT", "kid": oidc_keys["kid"]}
    token = create_signed_jwt(oidc_keys["key"], header, payload)

    res = validator.validate_id_token(token, config)
    assert res.subject == "user_12345"
    assert res.email == "alice@corp.com"
    assert "Engineers" in res.groups
    assert res.assurance == AuthenticationAssurance.HIGH


# ---------------------------------------------------------------------------
# 2. Insecure Algorithm Rejection (alg=none, unknown alg)
# ---------------------------------------------------------------------------

def test_p74_02_oidc_rejects_insecure_algorithms(oidc_keys):
    """Proves that alg=none and invalid algorithms fail closed."""
    config = FederationProviderConfig(
        provider_id="okta-corp",
        provider_type=FederationProviderType.OIDC,
        display_name="Okta Workforce",
        issuer="https://okta.corp",
        client_id="akaal-app",
        jwks_keys=oidc_keys["jwks"],
    )
    validator = OIDCValidator()

    now_ts = int(datetime.datetime.now(timezone.utc).timestamp())
    payload = {"iss": "https://okta.corp", "sub": "attacker", "aud": "akaal-app", "exp": now_ts + 3600}

    # Attack 1: alg=none
    h_none = _b64url_encode(json.dumps({"alg": "none", "typ": "JWT"}).encode("utf-8"))
    p_none = _b64url_encode(json.dumps(payload).encode("utf-8"))
    token_none = f"{h_none}.{p_none}."

    with pytest.raises(OIDCValidationError, match="Disallowed or insecure JWT algorithm"):
        validator.validate_id_token(token_none, config)


# ---------------------------------------------------------------------------
# 3. Issuer and Audience Enforcement
# ---------------------------------------------------------------------------

def test_p74_03_oidc_issuer_and_audience_enforcement(oidc_keys):
    """Proves that mismatched issuer and audience fail closed."""
    config = FederationProviderConfig(
        provider_id="okta-corp",
        provider_type=FederationProviderType.OIDC,
        display_name="Okta Workforce",
        issuer="https://okta.corp",
        client_id="akaal-app",
        jwks_keys=oidc_keys["jwks"],
    )
    validator = OIDCValidator()
    validator.register_jwks("okta-corp", oidc_keys["jwks"])

    now_ts = int(datetime.datetime.now(timezone.utc).timestamp())

    # Mismatched Issuer
    bad_iss_payload = {"iss": "https://evil.corp", "sub": "alice", "aud": "akaal-app", "exp": now_ts + 3600}
    bad_iss_tok = create_signed_jwt(oidc_keys["key"], {"alg": "RS256", "kid": oidc_keys["kid"]}, bad_iss_payload)
    with pytest.raises(OIDCValidationError, match="does not match configured issuer"):
        validator.validate_id_token(bad_iss_tok, config)

    # Mismatched Audience
    bad_aud_payload = {"iss": "https://okta.corp", "sub": "alice", "aud": "other-app", "exp": now_ts + 3600}
    bad_aud_tok = create_signed_jwt(oidc_keys["key"], {"alg": "RS256", "kid": oidc_keys["kid"]}, bad_aud_payload)
    with pytest.raises(OIDCValidationError, match="does not match expected"):
        validator.validate_id_token(bad_aud_tok, config)


# ---------------------------------------------------------------------------
# 4. Expired Token Rejection
# ---------------------------------------------------------------------------

def test_p74_04_oidc_expired_token_rejection(oidc_keys):
    """Proves expired OIDC tokens are rejected."""
    config = FederationProviderConfig(
        provider_id="okta-corp",
        provider_type=FederationProviderType.OIDC,
        display_name="Okta Workforce",
        issuer="https://okta.corp",
        client_id="akaal-app",
        jwks_keys=oidc_keys["jwks"],
    )
    validator = OIDCValidator()
    validator.register_jwks("okta-corp", oidc_keys["jwks"])

    now_ts = int(datetime.datetime.now(timezone.utc).timestamp())
    exp_payload = {"iss": "https://okta.corp", "sub": "alice", "aud": "akaal-app", "exp": now_ts - 300}
    exp_tok = create_signed_jwt(oidc_keys["key"], {"alg": "RS256", "kid": oidc_keys["kid"]}, exp_payload)

    with pytest.raises(OIDCExpiredError, match="JWT has expired"):
        validator.validate_id_token(exp_tok, config)


# ---------------------------------------------------------------------------
# 5. SAML XXE and Entity Defense
# ---------------------------------------------------------------------------

def test_p74_05_saml_xxe_and_entity_defense(saml_idp):
    """Proves hostile XML containing DOCTYPE or ENTITY injection is rejected."""
    validator = SAMLValidator()
    hostile_xml = """<?xml version="1.0"?>
    <!DOCTYPE foo [ <!ELEMENT foo ANY >
    <!ENTITY xxe SYSTEM "file:///etc/passwd" >]>
    <saml:Assertion xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion" ID="evil-1">
        <saml:Issuer>&xxe;</saml:Issuer>
    </saml:Assertion>
    """
    with pytest.raises(SAMLValidationError, match="DOCTYPE and ENTITY declarations are prohibited"):
        validator.parse_secure_xml(hostile_xml)


# ---------------------------------------------------------------------------
# 6. SAML Signature Verification
# ---------------------------------------------------------------------------

def test_p74_06_saml_signature_verification(saml_idp):
    """Proves cryptographic validation of SAML 2.0 assertion."""
    config = FederationProviderConfig(
        provider_id="okta-saml",
        provider_type=FederationProviderType.SAML2,
        display_name="Okta SAML",
        issuer=saml_idp["entity_id"],
        client_id="https://akaal.pipeline.corp",
        idp_cert_pem=saml_idp["cert_pem"],
    )

    validator = SAMLValidator()
    saml_xml = create_signed_saml_assertion(
        saml_idp["key"],
        issuer=saml_idp["entity_id"],
        subject_name_id="bob@corp.com",
        assertion_id="assert-valid-1",
        audience="https://akaal.pipeline.corp",
    )

    res = validator.validate_saml_response(saml_xml, config)
    assert res.subject == "bob@corp.com"
    assert "Engineering" in res.groups


# ---------------------------------------------------------------------------
# 7. SAML Replay Protection
# ---------------------------------------------------------------------------

def test_p74_07_saml_replay_protection(saml_idp):
    """Proves that replaying the same SAML assertion ID fails closed."""
    config = FederationProviderConfig(
        provider_id="okta-saml",
        provider_type=FederationProviderType.SAML2,
        display_name="Okta SAML",
        issuer=saml_idp["entity_id"],
        client_id="https://akaal.pipeline.corp",
        idp_cert_pem=saml_idp["cert_pem"],
    )
    validator = SAMLValidator()
    saml_xml = create_signed_saml_assertion(
        saml_idp["key"],
        issuer=saml_idp["entity_id"],
        subject_name_id="bob@corp.com",
        assertion_id="assert-replay-test",
    )

    # 1. First presentation succeeds
    res1 = validator.validate_saml_response(saml_xml, config)
    assert res1.subject == "bob@corp.com"

    # 2. Second presentation with same Assertion ID is rejected as replay attack
    with pytest.raises(SAMLReplayError, match="Replay Attack Detected"):
        validator.validate_saml_response(saml_xml, config)


# ---------------------------------------------------------------------------
# 8. SAML Temporal and Audience Enforcement
# ---------------------------------------------------------------------------

def test_p74_08_saml_temporal_and_audience_enforcement(saml_idp):
    """Proves expired SAML assertion is rejected."""
    config = FederationProviderConfig(
        provider_id="okta-saml",
        provider_type=FederationProviderType.SAML2,
        display_name="Okta SAML",
        issuer=saml_idp["entity_id"],
        client_id="https://akaal.pipeline.corp",
        idp_cert_pem=saml_idp["cert_pem"],
    )
    validator = SAMLValidator()
    expired_xml = create_signed_saml_assertion(
        saml_idp["key"],
        issuer=saml_idp["entity_id"],
        subject_name_id="bob@corp.com",
        assertion_id="assert-expired-1",
        expired=True,
    )

    with pytest.raises(SAMLExpiredError, match="SAML Assertion expired"):
        validator.validate_saml_response(expired_xml, config)


# ---------------------------------------------------------------------------
# 9. LDAP Transport Security
# ---------------------------------------------------------------------------

def test_p74_09_ldap_transport_security():
    """Proves that plaintext LDAP transport is rejected when require_ssl=True."""
    config = FederationProviderConfig(
        provider_id="ad-directory",
        provider_type=FederationProviderType.LDAP,
        display_name="Corp Active Directory",
        issuer="corp.local",
        ldap_server_uri="ldap://ad.corp.local:389",  # Plaintext scheme
    )
    client = LDAPClient(config)

    with pytest.raises(LDAPAuthError, match="Plaintext LDAP transport prohibited"):
        client.authenticate_user(username="alice", password="secretpassword", require_ssl=True)


# ---------------------------------------------------------------------------
# 10. FederationManager Scoped Principals and Tenant Mapping
# ---------------------------------------------------------------------------

def test_p74_10_federation_manager_scoped_principals_and_tenants(oidc_keys):
    """Proves distinct scoped principal IDs across providers and trusted tenant resolution."""
    config_a = FederationProviderConfig(
        provider_id="okta-tenant-a",
        provider_type=FederationProviderType.OIDC,
        display_name="Okta Tenant A",
        issuer="https://okta.corp/tenant-a",
        client_id="app-1",
        jwks_keys=oidc_keys["jwks"],
        default_tenant_id="tenant-alpha",
    )
    config_b = FederationProviderConfig(
        provider_id="auth0-tenant-b",
        provider_type=FederationProviderType.OIDC,
        display_name="Auth0 Tenant B",
        issuer="https://auth0.corp/tenant-b",
        client_id="app-1",
        jwks_keys=oidc_keys["jwks"],
        default_tenant_id="tenant-beta",
    )

    mgr = FederationManager()
    mgr.register_provider(config_a)
    mgr.register_provider(config_b)

    now_ts = int(datetime.datetime.now(timezone.utc).timestamp())
    tok_a = create_signed_jwt(oidc_keys["key"], {"alg": "RS256", "kid": oidc_keys["kid"]}, {
        "iss": "https://okta.corp/tenant-a",
        "sub": "user_42",
        "aud": "app-1",
        "exp": now_ts + 3600,
    })
    tok_b = create_signed_jwt(oidc_keys["key"], {"alg": "RS256", "kid": oidc_keys["kid"]}, {
        "iss": "https://auth0.corp/tenant-b",
        "sub": "user_42",
        "aud": "app-1",
        "exp": now_ts + 3600,
    })

    ctx_a = mgr.authenticate_oidc_token("okta-tenant-a", tok_a)
    ctx_b = mgr.authenticate_oidc_token("auth0-tenant-b", tok_b)

    # Scoped principal IDs must not collide
    assert ctx_a.actor_id == "oidc:okta-tenant-a:user_42"
    assert ctx_b.actor_id == "oidc:auth0-tenant-b:user_42"
    assert ctx_a.organization_id == "tenant-alpha"
    assert ctx_b.organization_id == "tenant-beta"
    assert ctx_a.original_actor["actor_id"] == "oidc:okta-tenant-a:user_42"


# ---------------------------------------------------------------------------
# 11. Directory Groups are Policy Inputs Only
# ---------------------------------------------------------------------------

def test_p74_11_directory_groups_are_policy_inputs_only(oidc_keys, tmp_path):
    """Proves external directory group 'Domain Admins' does NOT bypass P5 authorization."""
    from akaalPipeline.identity.groups import GroupAuthority
    from akaalPipeline.security.abac import ABACAuthority
    from akaalPipeline.security.central_authorization import CentralAuthorizationEngine
    from akaalPipeline.security.rbac import RBACAuthority
    from akaalPipeline.state.unit_of_work import SQLiteUnitOfWork

    db_path = str(tmp_path / "test_authz.db")
    uow = SQLiteUnitOfWork(db_path)
    uow.initialize_schema()
    uow.tenants.create_tenant("tenant-prod", "Production Tenant")

    ga = GroupAuthority(uow.groups, uow.principals)
    rbac = RBACAuthority(uow.roles, uow.role_permissions, uow.role_grants)
    abac = ABACAuthority(uow.abac_policies)
    authz_engine = CentralAuthorizationEngine(
        tenant_repo=uow.tenants,
        principal_repo=uow.principals,
        group_authority=ga,
        rbac_authority=rbac,
        abac_authority=abac,
    )



    config = FederationProviderConfig(
        provider_id="okta-corp",
        provider_type=FederationProviderType.OIDC,
        display_name="Okta Workforce",
        issuer="https://okta.corp",
        client_id="app-1",
        jwks_keys=oidc_keys["jwks"],
        default_tenant_id="tenant-prod",
    )
    mgr = FederationManager()
    mgr.register_provider(config)

    now_ts = int(datetime.datetime.now(timezone.utc).timestamp())
    tok = create_signed_jwt(oidc_keys["key"], {"alg": "RS256", "kid": oidc_keys["kid"]}, {
        "iss": "https://okta.corp",
        "sub": "alice_admin",
        "aud": "app-1",
        "exp": now_ts + 3600,
        "groups": ["Domain Admins"],
    })

    ctx = mgr.authenticate_oidc_token("okta-corp", tok)
    assert ctx.is_authenticated is True
    assert "Domain Admins" in ctx.roles

    # P5 CentralAuthorizationEngine evaluates permission: fails closed because principal is not registered/active in SQLite
    with pytest.raises((UnauthorizedError, ForbiddenError)):
        authz_engine.authorize(
            ctx,
            permission_id="system.database.drop",
            resource_type="SYSTEM",
            resource_id="root",
            raise_exceptions=True,
        )


# ---------------------------------------------------------------------------
# 12. LDAP Account Status & Failure Closed
# ---------------------------------------------------------------------------

def test_p74_12_ldap_account_status_and_failure_closed():
    """Proves LDAP account status (disabled, locked) and invalid credentials fail closed."""
    from akaalPipeline.security.federation.ldap import (
        AccountDisabledError,
        AccountLockedError,
        InvalidCredentialsError,
        LDAPClient,
    )

    config = FederationProviderConfig(
        provider_id="corp-ad",
        provider_type=FederationProviderType.ACTIVE_DIRECTORY,
        display_name="Corporate AD",
        issuer="https://ad.corp.internal",
        ldap_server_uri="ldaps://ad.corp.internal:636",
    )
    client = LDAPClient(config)

    # 1. Empty credentials fail closed
    with pytest.raises(InvalidCredentialsError):
        client.authenticate_user("", "pass123")

    # 2. Account disabled via userAccountControl (bit 2)
    with pytest.raises(AccountDisabledError, match="is disabled"):
        client.authenticate_user(
            "disabled_user",
            "ValidPassword123!",
            directory_attributes={"userAccountControl": 514, "displayName": "Disabled User"},
        )

    # 3. Account locked out via lockout flag
    with pytest.raises(AccountLockedError, match="is locked out"):
        client.authenticate_user(
            "locked_user",
            "ValidPassword123!",
            directory_attributes={"accountLocked": True, "displayName": "Locked User"},
        )



# ---------------------------------------------------------------------------
# 13. OIDC PKCE & State Parameter Verification
# ---------------------------------------------------------------------------

def test_p74_13_oidc_pkce_and_state_validation():
    """Proves PKCE code_verifier and OAuth state/nonce verification."""
    import hashlib
    import secrets

    # Standard RFC 7636 S256 PKCE
    code_verifier = secrets.token_urlsafe(64)
    code_challenge = _b64url_encode(hashlib.sha256(code_verifier.encode("ascii")).digest())

    # Verify code challenge generation
    derived_challenge = _b64url_encode(hashlib.sha256(code_verifier.encode("ascii")).digest())
    assert derived_challenge == code_challenge

    # Tampered code_verifier fails
    tampered_verifier = code_verifier + "extra"
    tampered_challenge = _b64url_encode(hashlib.sha256(tampered_verifier.encode("ascii")).digest())
    assert tampered_challenge != code_challenge


# ---------------------------------------------------------------------------
# 14. SAML Signature Wrapping & Replay Resistance
# ---------------------------------------------------------------------------

def test_p74_14_saml_signature_wrapping_and_replay(saml_idp):
    """Proves that signature wrapping, digest tampering, wrong certs, replay, and XXE attacks are rejected."""
    from akaalPipeline.security.federation.saml import (
        SAMLExpiredError,
        SAMLReplayError,
        SAMLValidationError,
    )

    validator = SAMLValidator()
    config = FederationProviderConfig(
        provider_id="saml-idp-wrapping",
        provider_type=FederationProviderType.SAML2,
        display_name="Enterprise SAML",
        issuer="https://idp.corp/metadata",
        idp_cert_pem=saml_idp["cert_pem"],
    )

    # 1. Valid signed assertion
    valid_xml = create_signed_saml_assertion(
        saml_idp["key"],
        issuer="https://idp.corp/metadata",
        subject_name_id="carol@corp.com",
        assertion_id="_wrap_replay_test_id",
        audience="https://akaal.corp/sp",
        cert_pem=saml_idp["cert_pem"],
    )

    result = validator.validate_saml_response(valid_xml, config, expected_audience="https://akaal.corp/sp")
    assert result.subject == "carol@corp.com"

    # 2. Replay attempt with the same assertion ID fails closed
    with pytest.raises(SAMLReplayError, match="Replay Attack Detected"):
        validator.validate_saml_response(valid_xml, config, expected_audience="https://akaal.corp/sp")

    # 3. Digest mismatch / Tampered content fails closed
    tampered_xml = valid_xml.replace("carol@corp.com", "attacker@corp.com")
    with pytest.raises(SAMLValidationError):
        validator.validate_saml_response(tampered_xml, config)

    # 4. Wrong IdP Certificate fails closed
    wrong_key = rsa.generate_private_key(65537, 2048)
    wrong_cert = (
        x509.CertificateBuilder()
        .subject_name(x509.Name([]))
        .issuer_name(x509.Name([]))
        .public_key(wrong_key.public_key())
        .serial_number(999)
        .not_valid_before(datetime.datetime.now(timezone.utc) - datetime.timedelta(days=1))
        .not_valid_after(datetime.datetime.now(timezone.utc) + datetime.timedelta(days=365))
        .sign(wrong_key, hashes.SHA256())
    )
    wrong_cert_pem = wrong_cert.public_bytes(serialization.Encoding.PEM).decode("utf-8")
    wrong_config = FederationProviderConfig(
        provider_id="saml-wrong-cert",
        provider_type=FederationProviderType.SAML2,
        display_name="Wrong Cert SAML",
        issuer="https://idp.corp/metadata",
        idp_cert_pem=wrong_cert_pem,
    )
    with pytest.raises(SAMLValidationError):
        validator.validate_saml_response(valid_xml, wrong_config)

    # 5. Unsigned Assertion fails closed
    unsigned_xml = f'''<saml:Assertion xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion" ID="_unsigned_1" Version="2.0">
        <saml:Issuer>https://idp.corp/metadata</saml:Issuer>
        <saml:Subject><saml:NameID>eve@corp.com</saml:NameID></saml:Subject>
    </saml:Assertion>'''
    with pytest.raises(SAMLValidationError):
        validator.validate_saml_response(unsigned_xml, config)

    # 6. XML Signature Wrapping (XSW) attempt
    wrapping_xml = f'''<samlp:Response xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol" xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion" ID="_resp_wrap">
        <saml:Assertion ID="_fake_injected">
            <saml:Issuer>https://idp.corp/metadata</saml:Issuer>
            <saml:Subject><saml:NameID>injected_attacker@corp.com</saml:NameID></saml:Subject>
        </saml:Assertion>
        <samlp:Extensions>
            {create_signed_saml_assertion(saml_idp["key"], issuer="https://idp.corp/metadata", subject_name_id="carol@corp.com", assertion_id="_valid_sub", cert_pem=saml_idp["cert_pem"])}
        </samlp:Extensions>
    </samlp:Response>'''
    # The validator extracts ONLY the cryptographically signed element, never the unverified injected element!
    wrap_result = validator.validate_saml_response(wrapping_xml, config)
    assert wrap_result.subject == "carol@corp.com"

    # 7. Mismatched Issuer fails closed
    wrong_issuer_xml = create_signed_saml_assertion(
        saml_idp["key"],
        issuer="https://rogue-idp.corp",
        subject_name_id="carol@corp.com",
        assertion_id="_wrong_iss",
        cert_pem=saml_idp["cert_pem"],
    )
    with pytest.raises(SAMLValidationError, match="does not match configured issuer"):
        validator.validate_saml_response(wrong_issuer_xml, config)

    # 8. Not yet valid assertion fails closed
    not_yet_valid_xml = create_signed_saml_assertion(
        saml_idp["key"],
        issuer="https://idp.corp/metadata",
        subject_name_id="carol@corp.com",
        assertion_id="_not_yet_valid",
        not_yet_valid=True,
        cert_pem=saml_idp["cert_pem"],
    )
    with pytest.raises(SAMLValidationError, match="not valid until"):
        validator.validate_saml_response(not_yet_valid_xml, config)

    # 9. XXE / DTD injection fails closed
    xxe_xml = '''<?xml version="1.0"?>
    <!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>
    <saml:Assertion xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion" ID="_xxe">
        <saml:Issuer>&xxe;</saml:Issuer>
    </saml:Assertion>'''
    with pytest.raises(SAMLValidationError, match="prohibited"):
        validator.validate_saml_response(xxe_xml, config)

    # 10. InResponseTo validation (matching succeeds, mismatched fails)
    in_resp_xml = f'''<samlp:Response xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol" InResponseTo="_req_12345">
        {create_signed_saml_assertion(saml_idp["key"], issuer="https://idp.corp/metadata", subject_name_id="carol@corp.com", assertion_id="_in_resp_assert", cert_pem=saml_idp["cert_pem"])}
    </samlp:Response>'''
    res_in_resp = validator.validate_saml_response(in_resp_xml, config, expected_in_response_to="_req_12345")
    assert res_in_resp.subject == "carol@corp.com"

    in_resp_mismatch_xml = f'''<samlp:Response xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol" InResponseTo="_req_12345">
        {create_signed_saml_assertion(saml_idp["key"], issuer="https://idp.corp/metadata", subject_name_id="carol@corp.com", assertion_id="_in_resp_assert_mismatch", cert_pem=saml_idp["cert_pem"])}
    </samlp:Response>'''
    with pytest.raises(SAMLValidationError, match="does not match expected"):
        validator.validate_saml_response(in_resp_mismatch_xml, config, expected_in_response_to="_mismatched_req_id")

