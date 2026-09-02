"""tests.security.test_p72_pki_certificate_lifecycle
===================================================
Comprehensive Unit, Integration, and Hostile Test Suite for P7.2:
TLS / mTLS + PKI + Certificate Lifecycle Consumer.
"""

import datetime
from datetime import timezone
import pytest
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, ExtensionOID, NameOID

from akaalPipeline.contracts.enums import CertificateLifecycleState
from akaalPipeline.security.config import SecurityBaselineConfig
from akaalPipeline.security.pki import (
    CertificateExpiredError,
    CertificateLifecycleManager,
    CertificateNotYetValidError,
    CertificateRevokedError,
    CertificateValidationError,
    CertificateValidator,
    UntrustedIssuerError,
)


@pytest.fixture
def ca_material():
    """Generates a real self-signed Root CA for local cryptographic tests."""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048, backend=default_backend())
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "AKAAL Test PKI Root CA"),
        x509.NameAttribute(NameOID.COMMON_NAME, "AKAAL Test Root CA"),
    ])
    now = datetime.datetime.now(timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(private_key.public_key())
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
        .sign(private_key, hashes.SHA256(), default_backend())
    )
    ca_pem = cert.public_bytes(serialization.Encoding.PEM).decode("utf-8")
    return {"key": private_key, "cert": cert, "pem": ca_pem}


def generate_leaf_cert(
    ca_key,
    ca_cert,
    common_name="engine.akaal.internal",
    dns_sans=None,
    ip_sans=None,
    days_valid=30,
    start_offset_days=0,
):
    """Generates a leaf certificate signed by the test CA."""
    leaf_key = rsa.generate_private_key(public_exponent=65537, key_size=2048, backend=default_backend())
    subject = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "AKAAL Test Leaf"),
        x509.NameAttribute(NameOID.COMMON_NAME, common_name),
    ])
    now = datetime.datetime.now(timezone.utc)
    nvb = now + datetime.timedelta(days=start_offset_days)
    nva = nvb + datetime.timedelta(days=days_valid)

    san_list = []
    if dns_sans:
        for dns in dns_sans:
            san_list.append(x509.DNSName(dns))
    if ip_sans:
        import ipaddress
        for ip in ip_sans:
            san_list.append(x509.IPAddress(ipaddress.ip_address(ip)))

    builder = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(ca_cert.subject)
        .public_key(leaf_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(nvb)
        .not_valid_after(nva)
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(
            x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH, ExtendedKeyUsageOID.CLIENT_AUTH]),
            critical=False,
        )
    )
    if san_list:
        builder = builder.add_extension(x509.SubjectAlternativeName(san_list), critical=False)

    leaf_cert = builder.sign(ca_key, hashes.SHA256(), default_backend())
    leaf_pem = leaf_cert.public_bytes(serialization.Encoding.PEM).decode("utf-8")
    return {"key": leaf_key, "cert": leaf_cert, "pem": leaf_pem}


# ---------------------------------------------------------------------------
# 1. Certificate Parsing & Metadata Extraction
# ---------------------------------------------------------------------------

def test_p72_01_parse_and_metadata_extraction(ca_material):
    """Proves X.509 certificate parsing and truthful metadata extraction."""
    validator = CertificateValidator()
    leaf = generate_leaf_cert(
        ca_material["key"],
        ca_material["cert"],
        common_name="api.akaal.internal",
        dns_sans=["api.akaal.internal", "api-backup.akaal.internal"],
        ip_sans=["10.0.0.1"],
    )

    cert_obj = validator.parse_pem(leaf["pem"])
    meta = validator.extract_metadata(cert_obj)

    assert meta.subject.startswith("CN=api.akaal.internal")
    assert "api.akaal.internal" in meta.dns_sans
    assert "api-backup.akaal.internal" in meta.dns_sans
    assert "10.0.0.1" in meta.ip_sans
    assert "server_auth" in meta.extended_key_usage
    assert "client_auth" in meta.extended_key_usage
    assert meta.is_ca is False


# ---------------------------------------------------------------------------
# 2. Cryptographic CA Trust Anchor Verification
# ---------------------------------------------------------------------------

def test_p72_02_cryptographic_ca_chain_validation(ca_material):
    """Proves cryptographic signature verification against trusted CA root."""
    validator = CertificateValidator()
    leaf = generate_leaf_cert(ca_material["key"], ca_material["cert"], common_name="engine.akaal.internal")
    cert_obj = validator.parse_pem(leaf["pem"])

    # Valid validation against CA
    meta = validator.validate_certificate(cert_obj, trust_anchors=[ca_material["cert"]])
    assert meta.state == CertificateLifecycleState.VALIDATED

    # Validation against empty CA anchors must fail closed
    with pytest.raises(UntrustedIssuerError):
        validator.validate_certificate(cert_obj, trust_anchors=[])


# ---------------------------------------------------------------------------
# 3. Temporal Validity Enforcement
# ---------------------------------------------------------------------------

def test_p72_03_temporal_validity_enforcement(ca_material):
    """Proves temporal validity: expired and not-yet-valid certificates are rejected."""
    validator = CertificateValidator()

    # Expired Certificate (ended 5 days ago)
    expired_leaf = generate_leaf_cert(
        ca_material["key"],
        ca_material["cert"],
        days_valid=10,
        start_offset_days=-20,
    )
    with pytest.raises(CertificateExpiredError):
        validator.validate_certificate(
            validator.parse_pem(expired_leaf["pem"]),
            trust_anchors=[ca_material["cert"]],
        )

    # Not-Yet-Valid Certificate (starts in 5 days)
    future_leaf = generate_leaf_cert(
        ca_material["key"],
        ca_material["cert"],
        days_valid=30,
        start_offset_days=5,
    )
    with pytest.raises(CertificateNotYetValidError):
        validator.validate_certificate(
            validator.parse_pem(future_leaf["pem"]),
            trust_anchors=[ca_material["cert"]],
        )


# ---------------------------------------------------------------------------
# 4. SAN and Hostname Verification
# ---------------------------------------------------------------------------

def test_p72_04_san_and_hostname_verification(ca_material):
    """Proves strict SAN and hostname matching (DNS, Wildcard, IP)."""
    validator = CertificateValidator()
    leaf = generate_leaf_cert(
        ca_material["key"],
        ca_material["cert"],
        common_name="db.prod.akaal.internal",
        dns_sans=["*.db.akaal.internal", "db-primary.akaal.internal"],
        ip_sans=["192.168.1.100"],
    )
    cert_obj = validator.parse_pem(leaf["pem"])

    # 1. Matching exact DNS SAN
    meta = validator.validate_certificate(
        cert_obj,
        trust_anchors=[ca_material["cert"]],
        expected_hostname="db-primary.akaal.internal",
    )
    assert meta.state == CertificateLifecycleState.VALIDATED

    # 2. Matching Wildcard SAN
    meta_wild = validator.validate_certificate(
        cert_obj,
        trust_anchors=[ca_material["cert"]],
        expected_hostname="node1.db.akaal.internal",
    )
    assert meta_wild.state == CertificateLifecycleState.VALIDATED

    # 3. Matching IP SAN
    meta_ip = validator.validate_certificate(
        cert_obj,
        trust_anchors=[ca_material["cert"]],
        expected_hostname="192.168.1.100",
    )
    assert meta_ip.state == CertificateLifecycleState.VALIDATED

    # 4. Mismatched hostname fails closed
    with pytest.raises(CertificateValidationError, match="do not match expected hostname"):
        validator.validate_certificate(
            cert_obj,
            trust_anchors=[ca_material["cert"]],
            expected_hostname="attacker.evil.com",
        )


# ---------------------------------------------------------------------------
# 5. CRL Revocation Enforcement
# ---------------------------------------------------------------------------

def test_p72_05_crl_revocation_enforcement(ca_material):
    """Proves that revoked certificates are detected and rejected via CRL."""
    validator = CertificateValidator()
    leaf = generate_leaf_cert(ca_material["key"], ca_material["cert"], common_name="revoked.akaal.internal")
    cert_obj = validator.parse_pem(leaf["pem"])

    # Build CRL revoking the leaf serial number
    now = datetime.datetime.now(timezone.utc)
    revoked_cert_builder = (
        x509.RevokedCertificateBuilder()
        .serial_number(cert_obj.serial_number)
        .revocation_date(now)
    )
    crl = (
        x509.CertificateRevocationListBuilder()
        .issuer_name(ca_material["cert"].subject)
        .last_update(now - datetime.timedelta(days=1))
        .next_update(now + datetime.timedelta(days=7))
        .add_revoked_certificate(revoked_cert_builder.build())
        .sign(ca_material["key"], hashes.SHA256(), default_backend())
    )

    with pytest.raises(CertificateRevokedError, match="is revoked"):
        validator.validate_certificate(
            cert_obj,
            trust_anchors=[ca_material["cert"]],
            crl_list=[crl],
        )


# ---------------------------------------------------------------------------
# 6. Configurable Expiry Monitoring & Lifecycle Transitions
# ---------------------------------------------------------------------------

def test_p72_06_configurable_expiry_monitoring(ca_material):
    """Proves configurable warning threshold moves ACTIVE -> EXPIRING -> EXPIRED."""
    # Configure custom warning window: 15 days (1,296,000s)
    config = SecurityBaselineConfig(pki_cert_expiry_warning_seconds=1296000)
    mgr = CertificateLifecycleManager(config=config)
    mgr.register_trust_anchor(ca_material["pem"])

    # Certificate valid for 20 days
    leaf = generate_leaf_cert(ca_material["key"], ca_material["cert"], days_valid=20)
    active_meta = mgr.import_and_activate_certificate(leaf["pem"], cert_id="cert-exp-1")
    assert active_meta.state == CertificateLifecycleState.ACTIVE

    # At day 0: remaining = 20 days > 15 days warning threshold -> Stays ACTIVE
    eval_now = datetime.datetime.now(timezone.utc)
    st = mgr.evaluate_lifecycle_state("cert-exp-1", now=eval_now)
    assert st.state == CertificateLifecycleState.ACTIVE

    # At day 10: remaining = 10 days <= 15 days warning threshold -> Transitions to EXPIRING
    eval_d10 = eval_now + datetime.timedelta(days=10)
    st_d10 = mgr.evaluate_lifecycle_state("cert-exp-1", now=eval_d10)
    assert st_d10.state == CertificateLifecycleState.EXPIRING

    # At day 25: past expiration -> Transitions to EXPIRED
    eval_d25 = eval_now + datetime.timedelta(days=25)
    st_d25 = mgr.evaluate_lifecycle_state("cert-exp-1", now=eval_d25)
    assert st_d25.state == CertificateLifecycleState.EXPIRED


# ---------------------------------------------------------------------------
# 7. Dual-Certificate Controlled Rotation
# ---------------------------------------------------------------------------

def test_p72_07_controlled_dual_cert_rotation(ca_material):
    """Proves dual-certificate rotation: new cert becomes ACTIVE, old cert becomes RETIRING."""
    mgr = CertificateLifecycleManager()
    mgr.register_trust_anchor(ca_material["pem"])

    old_leaf = generate_leaf_cert(ca_material["key"], ca_material["cert"], common_name="old.akaal.internal")
    mgr.import_and_activate_certificate(old_leaf["pem"], cert_id="cert-old")

    new_leaf = generate_leaf_cert(ca_material["key"], ca_material["cert"], common_name="new.akaal.internal")
    new_meta, old_meta = mgr.rotate_certificate("cert-old", new_leaf["pem"])

    assert new_meta.state == CertificateLifecycleState.ACTIVE
    assert old_meta.state == CertificateLifecycleState.RETIRING


# ---------------------------------------------------------------------------
# 8. P6 Alert Integration on Degradation
# ---------------------------------------------------------------------------

def test_p72_08_p6_alert_integration(ca_material):
    """Proves that certificate degradation triggers P6 alert notifications."""
    alerts_received = []

    def mock_p6_alert_sink(event_type, msg, details):
        alerts_received.append({"event": event_type, "message": msg, "details": details})

    config = SecurityBaselineConfig(pki_cert_expiry_warning_seconds=864000)  # 10 days
    mgr = CertificateLifecycleManager(config=config, alert_callback=mock_p6_alert_sink)
    mgr.register_trust_anchor(ca_material["pem"])

    leaf = generate_leaf_cert(ca_material["key"], ca_material["cert"], days_valid=12)
    mgr.import_and_activate_certificate(leaf["pem"], cert_id="cert-alert-test")

    # Fast forward to 5 days before expiration (within warning window)
    now = datetime.datetime.now(timezone.utc) + datetime.timedelta(days=8)
    mgr.evaluate_lifecycle_state("cert-alert-test", now=now)

    assert len(alerts_received) == 1
    assert alerts_received[0]["event"] == "CERTIFICATE_EXPIRING"
    assert "cert-alert-test" in alerts_received[0]["message"]


# ---------------------------------------------------------------------------
# 9. Intermediate CA Chain Validation (Leaf -> Intermediate -> Root CA)
# ---------------------------------------------------------------------------

def test_p72_09_intermediate_ca_chain_validation(ca_material):
    """Proves cryptographic validation across a multi-tier CA hierarchy."""
    # 1. Create Intermediate CA signed by Root CA
    inter_key = rsa.generate_private_key(public_exponent=65537, key_size=2048, backend=default_backend())
    inter_subject = x509.Name([
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "AKAAL Intermediate CA"),
        x509.NameAttribute(NameOID.COMMON_NAME, "AKAAL Intermediate Level 1"),
    ])
    now = datetime.datetime.now(timezone.utc)
    inter_cert = (
        x509.CertificateBuilder()
        .subject_name(inter_subject)
        .issuer_name(ca_material["cert"].subject)
        .public_key(inter_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(days=1))
        .not_valid_after(now + datetime.timedelta(days=180))
        .add_extension(x509.BasicConstraints(ca=True, path_length=1), critical=True)
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
        .sign(ca_material["key"], hashes.SHA256(), default_backend())
    )

    # 2. Create Leaf cert signed by Intermediate CA
    leaf = generate_leaf_cert(inter_key, inter_cert, common_name="service.prod.akaal.internal")

    validator = CertificateValidator()
    leaf_obj = validator.parse_pem(leaf["pem"])

    # 3. Validate with intermediate cert supplied
    meta = validator.validate_certificate(
        leaf_obj,
        trust_anchors=[ca_material["cert"]],
        intermediate_certs=[inter_cert],
        expected_hostname="service.prod.akaal.internal",
        expected_purpose="server_auth",
    )
    assert meta.state == CertificateLifecycleState.VALIDATED
    assert meta.subject.startswith("CN=service.prod.akaal.internal")


# ---------------------------------------------------------------------------
# 10. Hostile Intermediate Chain & EKU Attacks
# ---------------------------------------------------------------------------

def test_p72_10_hostile_intermediate_and_eku_attacks(ca_material):
    """Proves hostile intermediate CA and EKU mismatch attacks fail closed."""
    validator = CertificateValidator()
    now = datetime.datetime.now(timezone.utc)

    # Attack 1: Non-CA Intermediate (ca=False) attempting to sign leaf
    fake_inter_key = rsa.generate_private_key(public_exponent=65537, key_size=2048, backend=default_backend())
    fake_inter_subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Fake Non-CA Intermediate")])
    fake_inter_cert = (
        x509.CertificateBuilder()
        .subject_name(fake_inter_subject)
        .issuer_name(ca_material["cert"].subject)
        .public_key(fake_inter_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(days=1))
        .not_valid_after(now + datetime.timedelta(days=30))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)  # ca=False!
        .sign(ca_material["key"], hashes.SHA256(), default_backend())
    )

    leaf = generate_leaf_cert(fake_inter_key, fake_inter_cert, common_name="victim.akaal.internal")
    leaf_obj = validator.parse_pem(leaf["pem"])

    with pytest.raises(CertificateValidationError, match="is not a CA"):
        validator.validate_certificate(
            leaf_obj,
            trust_anchors=[ca_material["cert"]],
            intermediate_certs=[fake_inter_cert],
        )

    # Attack 2: Expired Intermediate CA
    exp_inter_key = rsa.generate_private_key(public_exponent=65537, key_size=2048, backend=default_backend())
    exp_inter_cert = (
        x509.CertificateBuilder()
        .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Expired Intermediate")]))
        .issuer_name(ca_material["cert"].subject)
        .public_key(exp_inter_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(days=20))
        .not_valid_after(now - datetime.timedelta(days=5))  # Expired!
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
        .sign(ca_material["key"], hashes.SHA256(), default_backend())
    )

    exp_leaf = generate_leaf_cert(exp_inter_key, exp_inter_cert, common_name="victim.akaal.internal")
    with pytest.raises(CertificateExpiredError, match="Certificate has expired"):
        validator.validate_certificate(
            validator.parse_pem(exp_leaf["pem"]),
            trust_anchors=[ca_material["cert"]],
            intermediate_certs=[exp_inter_cert],
        )

