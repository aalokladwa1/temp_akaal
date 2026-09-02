"""tests.security.test_p73_spiffe_spire_workload_identity
======================================================
Comprehensive Unit, Integration, and Hostile Test Suite for P7.3:
Workload Identity + SPIFFE / SPIRE Integration.
"""

import datetime
from datetime import timezone
import pytest
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from akaalPipeline.contracts.enums import (
    AuthenticationAssurance,
    AuthenticationState,
    CredentialMechanism,
    PrincipalType,
)
from akaalPipeline.security.spiffe import (
    SpiffeExpiredError,
    SpiffeID,
    SpiffeSVIDValidator,
    SpiffeTrustDomainMismatchError,
    SpiffeValidationError,
    SpireWorkloadClient,
)


@pytest.fixture
def spiffe_ca():
    """Generates a SPIFFE Trust Bundle Root CA for 'spiffe://akaal.corp'."""
    ca_key = rsa.generate_private_key(public_exponent=65537, key_size=2048, backend=default_backend())
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "AKAAL SPIFFE CA"),
        x509.NameAttribute(NameOID.COMMON_NAME, "akaal.corp SPIFFE Root"),
    ])
    now = datetime.datetime.now(timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(ca_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(days=1))
        .not_valid_after(now + datetime.timedelta(days=365))
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                content_commitment=False,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=True,
                crl_sign=True,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .sign(ca_key, hashes.SHA256(), default_backend())
    )
    return {"key": ca_key, "cert": cert, "trust_domain": "akaal.corp"}


def generate_svid(
    ca_key,
    ca_cert,
    spiffe_uri="spiffe://akaal.corp/sa/pipeline",
    days_valid=30,
    start_offset_days=0,
    include_san=True,
    extra_uris=None,
):
    """Generates an X.509 SVID signed by SPIFFE CA."""
    leaf_key = rsa.generate_private_key(public_exponent=65537, key_size=2048, backend=default_backend())
    subject = x509.Name([
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "AKAAL SVID"),
        x509.NameAttribute(NameOID.COMMON_NAME, "SPIFFE SVID"),
    ])
    now = datetime.datetime.now(timezone.utc)
    nvb = now + datetime.timedelta(days=start_offset_days)
    nva = nvb + datetime.timedelta(days=days_valid)

    builder = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(ca_cert.subject)
        .public_key(leaf_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(nvb)
        .not_valid_after(nva)
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
    )

    if include_san:
        san_list = [x509.UniformResourceIdentifier(spiffe_uri)]
        if extra_uris:
            for u in extra_uris:
                san_list.append(x509.UniformResourceIdentifier(u))
        builder = builder.add_extension(x509.SubjectAlternativeName(san_list), critical=False)

    leaf_cert = builder.sign(ca_key, hashes.SHA256(), default_backend())
    leaf_pem = leaf_cert.public_bytes(serialization.Encoding.PEM).decode("utf-8")
    return {"key": leaf_key, "cert": leaf_cert, "pem": leaf_pem, "uri": spiffe_uri}


# ---------------------------------------------------------------------------
# 1. SPIFFE URI Parsing & Structural Validation
# ---------------------------------------------------------------------------

def test_p73_01_spiffe_uri_parsing():
    """Proves RFC 3986 compliant SPIFFE URI validation and parsing."""
    valid_id = SpiffeID.parse("spiffe://akaal.corp/ns/prod/sa/pipeline")
    assert valid_id.trust_domain == "akaal.corp"
    assert valid_id.path == "/ns/prod/sa/pipeline"
    assert valid_id.uri == "spiffe://akaal.corp/ns/prod/sa/pipeline"

    # Reject malformed URIs
    with pytest.raises(SpiffeValidationError, match="Invalid SPIFFE URI"):
        SpiffeID.parse("https://akaal.corp/sa/pipeline")
    with pytest.raises(SpiffeValidationError, match="Invalid SPIFFE URI"):
        SpiffeID.parse("spiffe://")
    with pytest.raises(SpiffeValidationError, match="Invalid SPIFFE URI"):
        SpiffeID.parse("spiffe://akaal.corp")  # Missing path


# ---------------------------------------------------------------------------
# 2. X.509-SVID Validation with SPIFFE Trust Bundle
# ---------------------------------------------------------------------------

def test_p73_02_x509_svid_validation(spiffe_ca):
    """Proves cryptographic validation of X.509-SVID against SPIFFE trust bundle."""
    validator = SpiffeSVIDValidator()
    validator.register_trust_bundle("akaal.corp", [spiffe_ca["cert"]])

    svid = generate_svid(spiffe_ca["key"], spiffe_ca["cert"], spiffe_uri="spiffe://akaal.corp/sa/engine")
    verified_svid = validator.validate_x509_svid(
        svid["pem"],
        expected_trust_domain="akaal.corp",
        expected_workload_path="/sa/engine",
    )

    assert verified_svid.spiffe_id.uri == "spiffe://akaal.corp/sa/engine"
    assert verified_svid.is_expired is False


# ---------------------------------------------------------------------------
# 3. Trust Domain Mismatch Rejection
# ---------------------------------------------------------------------------

def test_p73_03_trust_domain_mismatch_fails_closed(spiffe_ca):
    """Proves that SVID with unexpected trust domain is rejected fail-closed."""
    validator = SpiffeSVIDValidator()
    validator.register_trust_bundle("akaal.corp", [spiffe_ca["cert"]])

    svid = generate_svid(spiffe_ca["key"], spiffe_ca["cert"], spiffe_uri="spiffe://akaal.corp/sa/pipeline")

    with pytest.raises(SpiffeTrustDomainMismatchError, match="does not match expected 'bank.corp'"):
        validator.validate_x509_svid(svid["pem"], expected_trust_domain="bank.corp")


# ---------------------------------------------------------------------------
# 4. Workload Path Mismatch Rejection
# ---------------------------------------------------------------------------

def test_p73_04_workload_path_mismatch_fails_closed(spiffe_ca):
    """Proves that SVID with wrong workload path is rejected fail-closed."""
    validator = SpiffeSVIDValidator()
    validator.register_trust_bundle("akaal.corp", [spiffe_ca["cert"]])

    svid = generate_svid(spiffe_ca["key"], spiffe_ca["cert"], spiffe_uri="spiffe://akaal.corp/sa/pipeline")

    with pytest.raises(SpiffeValidationError, match="workload path '/sa/pipeline' does not match expected '/sa/admin'"):
        validator.validate_x509_svid(svid["pem"], expected_workload_path="/sa/admin")


# ---------------------------------------------------------------------------
# 5. SPIRE Outage Lifetime Enforcement
# ---------------------------------------------------------------------------

def test_p73_05_spire_outage_never_extends_lifetime(spiffe_ca):
    """
    Proves that during a SPIRE outage, cached SVID can be used only while unexpired,
    and fails closed once expired (lifetime is never extended).
    """
    validator = SpiffeSVIDValidator()
    validator.register_trust_bundle("akaal.corp", [spiffe_ca["cert"]])

    # SVID valid for 10 days
    svid = generate_svid(spiffe_ca["key"], spiffe_ca["cert"], days_valid=10)
    verified = validator.validate_x509_svid(svid["pem"])

    client = SpireWorkloadClient(validator=validator, cached_svid=verified)

    # 1. Day 5 (Unexpired): Successfully retrieved
    now_d5 = datetime.datetime.now(timezone.utc) + datetime.timedelta(days=5)
    active = client.get_active_svid(now=now_d5)
    assert active.spiffe_id.uri == "spiffe://akaal.corp/sa/pipeline"

    # 2. Day 15 (Expired during outage): Fails closed with SpiffeExpiredError
    now_d15 = datetime.datetime.now(timezone.utc) + datetime.timedelta(days=15)
    with pytest.raises(SpiffeExpiredError, match="cannot extend lifetime during SPIRE outage"):
        client.get_active_svid(now=now_d15)


# ---------------------------------------------------------------------------
# 6. Canonical Pipeline Workload Context Minting
# ---------------------------------------------------------------------------

def test_p73_06_mint_canonical_workload_context(spiffe_ca):
    """Proves minting canonical PipelineActorContext with verified SPIFFE identity."""
    validator = SpiffeSVIDValidator()
    validator.register_trust_bundle("akaal.corp", [spiffe_ca["cert"]])

    svid = generate_svid(spiffe_ca["key"], spiffe_ca["cert"], spiffe_uri="spiffe://akaal.corp/sa/pipeline")
    verified = validator.validate_x509_svid(svid["pem"])

    ctx = validator.mint_pipeline_workload_context(
        svid=verified,
        organization_id="tenant-corp-a",
        target_workload="spiffe://akaal.corp/sa/engine",
    )

    assert ctx.actor_id == "spiffe://akaal.corp/sa/pipeline"
    assert ctx.actor_type == PrincipalType.WORKLOAD.value
    assert ctx.credential_mechanism == CredentialMechanism.SPIFFE_X509_SVID.value
    assert ctx.authentication_state == AuthenticationState.AUTHENTICATED.value
    assert ctx.authentication_assurance == AuthenticationAssurance.HIGH.value
    assert ctx.is_authenticated is True
    assert ctx.calling_workload == "spiffe://akaal.corp/sa/pipeline"
    assert ctx.target_workload == "spiffe://akaal.corp/sa/engine"


# ---------------------------------------------------------------------------
# 7. Hostile SPIFFE Attacks
# ---------------------------------------------------------------------------

def test_p73_07_hostile_spiffe_attacks(spiffe_ca):
    """Proves hostile attacks on SPIFFE identities fail closed."""
    validator = SpiffeSVIDValidator()
    validator.register_trust_bundle("akaal.corp", [spiffe_ca["cert"]])

    # Attack 1: Certificate without SPIFFE SAN
    no_san_leaf = generate_svid(spiffe_ca["key"], spiffe_ca["cert"], include_san=False)
    with pytest.raises(SpiffeValidationError, match="Certificate SAN does not contain a SPIFFE URI"):
        validator.validate_x509_svid(no_san_leaf["pem"])

    # Attack 2: Ambiguous Certificate with multiple SPIFFE URIs
    multi_san_leaf = generate_svid(
        spiffe_ca["key"],
        spiffe_ca["cert"],
        spiffe_uri="spiffe://akaal.corp/sa/worker1",
        extra_uris=["spiffe://akaal.corp/sa/admin"],
    )
    with pytest.raises(SpiffeValidationError, match="contains multiple SPIFFE URIs; ambiguous workload identity"):
        validator.validate_x509_svid(multi_san_leaf["pem"])

    # Attack 3: Expired SVID
    expired_svid = generate_svid(spiffe_ca["key"], spiffe_ca["cert"], days_valid=5, start_offset_days=-10)
    with pytest.raises(SpiffeExpiredError, match="has expired"):
        validator.validate_x509_svid(expired_svid["pem"])


# ---------------------------------------------------------------------------
# 8. SPIFFE JWT-SVID Validation
# ---------------------------------------------------------------------------

def test_p73_08_jwt_svid_validation():
    """Proves cryptographic validation of SPIFFE JWT-SVID."""
    import base64
    import json
    from cryptography.hazmat.primitives.asymmetric import padding

    # 1. Generate RSA key for SPIFFE JWT Issuer
    jwt_key = rsa.generate_private_key(public_exponent=65537, key_size=2048, backend=default_backend())
    pub_numbers = jwt_key.public_key().public_numbers()

    def _b64url(b: bytes) -> str:
        return base64.urlsafe_b64encode(b).decode("ascii").rstrip("=")

    n_b64 = _b64url(pub_numbers.n.to_bytes((pub_numbers.n.bit_length() + 7) // 8, "big"))
    e_b64 = _b64url(pub_numbers.e.to_bytes((pub_numbers.e.bit_length() + 7) // 8, "big"))

    jwks = {
        "keys": [
            {
                "kty": "RSA",
                "kid": "spiffe-key-1",
                "use": "sig",
                "alg": "RS256",
                "n": n_b64,
                "e": e_b64,
            }
        ]
    }

    # 2. Mint SPIFFE JWT-SVID
    now = datetime.datetime.now(timezone.utc)
    header = {"alg": "RS256", "typ": "JWT", "kid": "spiffe-key-1"}
    payload = {
        "sub": "spiffe://akaal.corp/sa/etl-service",
        "aud": ["engine.prod.akaal.internal"],
        "iss": "spiffe://akaal.corp",
        "iat": int(now.timestamp()),
        "exp": int((now + datetime.timedelta(minutes=30)).timestamp()),
    }

    h_b64 = _b64url(json.dumps(header).encode("utf-8"))
    p_b64 = _b64url(json.dumps(payload).encode("utf-8"))
    signing_input = f"{h_b64}.{p_b64}".encode("ascii")
    sig = jwt_key.sign(signing_input, padding.PKCS1v15(), hashes.SHA256())
    token = f"{h_b64}.{p_b64}.{_b64url(sig)}"

    # 3. Validate
    validator = SpiffeSVIDValidator()
    validator.register_jwt_bundle("akaal.corp", jwks)

    svid = validator.validate_jwt_svid(
        token=token,
        expected_audience="engine.prod.akaal.internal",
        expected_trust_domain="akaal.corp",
    )

    assert svid.spiffe_id.uri == "spiffe://akaal.corp/sa/etl-service"
    assert "engine.prod.akaal.internal" in svid.audience
    assert svid.is_expired is False


# ---------------------------------------------------------------------------
# 9. Hostile JWT-SVID Attacks
# ---------------------------------------------------------------------------

def test_p73_09_hostile_jwt_svid_attacks():
    """Proves hostile attacks on SPIFFE JWT-SVID fail closed."""
    import base64
    import json
    from cryptography.hazmat.primitives.asymmetric import padding

    jwt_key = rsa.generate_private_key(public_exponent=65537, key_size=2048, backend=default_backend())
    pub_numbers = jwt_key.public_key().public_numbers()

    def _b64url(b: bytes) -> str:
        return base64.urlsafe_b64encode(b).decode("ascii").rstrip("=")

    n_b64 = _b64url(pub_numbers.n.to_bytes((pub_numbers.n.bit_length() + 7) // 8, "big"))
    e_b64 = _b64url(pub_numbers.e.to_bytes((pub_numbers.e.bit_length() + 7) // 8, "big"))

    jwks = {
        "keys": [
            {
                "kty": "RSA",
                "kid": "spiffe-key-1",
                "use": "sig",
                "alg": "RS256",
                "n": n_b64,
                "e": e_b64,
            }
        ]
    }

    validator = SpiffeSVIDValidator()
    validator.register_jwt_bundle("akaal.corp", jwks)
    now = datetime.datetime.now(timezone.utc)

    # Attack 1: alg=none rejection
    none_h = _b64url(json.dumps({"alg": "none", "typ": "JWT"}).encode("utf-8"))
    none_p = _b64url(json.dumps({
        "sub": "spiffe://akaal.corp/sa/admin",
        "aud": ["engine.prod"],
        "exp": int((now + datetime.timedelta(hours=1)).timestamp()),
    }).encode("utf-8"))
    none_token = f"{none_h}.{none_p}."

    with pytest.raises(SpiffeValidationError, match="Disallowed or insecure"):
        validator.validate_jwt_svid(none_token, expected_audience="engine.prod")

    # Attack 2: Wrong Trust Domain
    h_b64 = _b64url(json.dumps({"alg": "RS256", "kid": "spiffe-key-1"}).encode("utf-8"))
    p_b64 = _b64url(json.dumps({
        "sub": "spiffe://foreign.corp/sa/worker",
        "aud": ["engine.prod"],
        "exp": int((now + datetime.timedelta(hours=1)).timestamp()),
    }).encode("utf-8"))
    sig = jwt_key.sign(f"{h_b64}.{p_b64}".encode("ascii"), padding.PKCS1v15(), hashes.SHA256())
    foreign_token = f"{h_b64}.{p_b64}.{_b64url(sig)}"

    with pytest.raises(SpiffeTrustDomainMismatchError, match="does not match expected"):
        validator.validate_jwt_svid(foreign_token, expected_audience="engine.prod", expected_trust_domain="akaal.corp")

    # Attack 3: Expired JWT-SVID
    exp_p_b64 = _b64url(json.dumps({
        "sub": "spiffe://akaal.corp/sa/worker",
        "aud": ["engine.prod"],
        "exp": int((now - datetime.timedelta(minutes=10)).timestamp()),  # Expired
    }).encode("utf-8"))
    exp_sig = jwt_key.sign(f"{h_b64}.{exp_p_b64}".encode("ascii"), padding.PKCS1v15(), hashes.SHA256())
    exp_token = f"{h_b64}.{exp_p_b64}.{_b64url(exp_sig)}"

    with pytest.raises(SpiffeExpiredError, match="has expired"):
        validator.validate_jwt_svid(exp_token, expected_audience="engine.prod")

