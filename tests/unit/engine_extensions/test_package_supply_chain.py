"""
tests.unit.engine_extensions.test_package_supply_chain
========================================================
Hostile verification of P7A.2 package integrity/signature/trust-root/revocation
enforcement for THIRD_PARTY_PACKAGE extension admission, and of the registration
gate that wires PackageIntegrityValidator into RegistrationTransaction.execute_register.

Also covers the hostile-review fixes:
  - the signature binds the CANONICAL MANIFEST ENVELOPE (extension_id, version,
    publisher_id, permissions, capabilities, provider/strategy identities, artifact
    digest), not just the bare digest -- mutating any bound field must invalidate
    the signature;
  - chain-of-trust policy enforcement: BasicConstraints CA flag on every issuer,
    KeyUsage keyCertSign on issuers, ExtendedKeyUsage code-signing purpose on the
    leaf, weak-signature-algorithm rejection, path-length constraints.

No mocks: real X.509 certificates, real RSA/EC signatures, real cryptography-library
verification throughout.
"""

from __future__ import annotations

import dataclasses
import hashlib
from datetime import datetime, timedelta, timezone

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, padding, rsa, utils
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

from akaalEngine.extensions.catalog.registry import ExtensionRegistry
from akaalEngine.extensions.errors.taxonomy import (
    PackageCertificateInvalidError,
    PackageCertificateRevokedError,
    PackageDigestMismatchError,
    PackageProvenanceMissingError,
    PackageSignatureInvalidError,
    PackageTrustRootUnknownError,
)
from akaalEngine.extensions.models import (
    AuthorityId,
    CompatibilityRange,
    ExtensionId,
    ExtensionManifest,
    ExtensionOrigin,
    ProviderContribution,
    ProviderId,
    StrategyContribution,
    StrategyId,
)
from akaalEngine.extensions.models.provenance import PackageProvenance
from akaalEngine.extensions.spi.authority_contract import (
    AuthorityContractDefinition,
    default_contract_registry,
)
from akaalEngine.extensions.supply_chain.canonical import canonical_envelope_digest
from akaalEngine.extensions.supply_chain.integrity import PackageIntegrityValidator
from akaalEngine.extensions.supply_chain.trust_store import PublisherTrustStore

ARTIFACT_BYTES = b"this is the extension package artifact content"


def _make_root(cn: str = "AKAAL Test Root", key_usage_cert_sign: bool = True):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, cn)])
    builder = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(timezone.utc) - timedelta(days=1))
        .not_valid_after(datetime.now(timezone.utc) + timedelta(days=365))
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
    )
    if key_usage_cert_sign is not None:
        builder = builder.add_extension(
            x509.KeyUsage(
                digital_signature=False, content_commitment=False, key_encipherment=False,
                data_encipherment=False, key_agreement=False, key_cert_sign=key_usage_cert_sign,
                crl_sign=True, encipher_only=False, decipher_only=False,
            ),
            critical=True,
        )
    cert = builder.sign(key, hashes.SHA256())
    return key, cert


def _make_leaf(
    root_key, root_cert, cn: str = "AKAAL Test Publisher",
    not_after_days: int = 365, not_before_days: int = -1,
    is_ca: bool = False, include_code_signing_eku: bool = True,
    eku_purpose=ExtendedKeyUsageOID.CODE_SIGNING,
):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, cn)])
    builder = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(root_cert.subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(timezone.utc) + timedelta(days=not_before_days))
        .not_valid_after(datetime.now(timezone.utc) + timedelta(days=not_after_days))
        .add_extension(x509.BasicConstraints(ca=is_ca, path_length=None), critical=True)
    )
    if include_code_signing_eku:
        builder = builder.add_extension(x509.ExtendedKeyUsage([eku_purpose]), critical=False)
    cert = builder.sign(root_key, hashes.SHA256())
    return key, cert


def _pem(cert) -> str:
    return cert.public_bytes(serialization.Encoding.PEM).decode()


def _sign_digest(private_key, digest_bytes: bytes) -> bytes:
    if isinstance(private_key, rsa.RSAPrivateKey):
        return private_key.sign(digest_bytes, padding.PKCS1v15(), utils.Prehashed(hashes.SHA256()))
    return private_key.sign(digest_bytes, ec.ECDSA(utils.Prehashed(hashes.SHA256())))


def _manifest(ext_id: str, version: str = "1.0.0", origin=ExtensionOrigin.THIRD_PARTY_PACKAGE, publisher_id: str = "acme-publisher") -> ExtensionManifest:
    default_contract_registry.register_contract(
        AuthorityContractDefinition(
            authority_id=AuthorityId("transport"),
            contract_version="1.0.0",
            description="Transport Contract",
        )
    )
    strat = StrategyContribution(
        strategy_id=StrategyId(f"{ext_id}-strat"),
        authority_id=AuthorityId("transport"),
        provider_id=ProviderId(f"{ext_id}-prov"),
        contract_version_range=CompatibilityRange("*"),
        strategy_factory=lambda: object(),
    )
    prov = ProviderContribution(
        provider_id=ProviderId(f"{ext_id}-prov"),
        vendor_name="Vendor",
        display_name="Provider",
        family="relational",
        strategies=(strat,),
    )
    return ExtensionManifest(
        extension_id=ExtensionId(ext_id),
        version=version,
        display_name=f"Extension {ext_id}",
        engine_version_range=CompatibilityRange(">=1.0.0"),
        origin=origin,
        publisher_id=publisher_id,
        provider_contributions=(prov,),
    )


def _valid_setup(extension_id="ext.pkg", version="1.0.0", publisher_id="acme-publisher"):
    """Builds a fully policy-compliant root/leaf pair, a manifest, and a provenance record
    whose signature covers the canonical envelope (manifest + artifact digest)."""
    root_key, root_cert = _make_root()
    leaf_key, leaf_cert = _make_leaf(root_key, root_cert)
    manifest = _manifest(extension_id, version, publisher_id=publisher_id)
    digest_hex = hashlib.sha256(ARTIFACT_BYTES).hexdigest()
    envelope_digest = canonical_envelope_digest(manifest, digest_hex)
    signature = _sign_digest(leaf_key, envelope_digest)
    provenance = PackageProvenance(
        extension_id=extension_id,
        version=version,
        artifact_digest_hex=digest_hex,
        digest_algorithm="sha256",
        signature=signature,
        signer_certificate_pem=_pem(leaf_cert),
        publisher_id=publisher_id,
    )
    store = PublisherTrustStore()
    store.register_trust_root("acme-root", _pem(root_cert))
    return provenance, store, leaf_cert, root_key, root_cert, manifest


# ---------------------------------------------------------------------------
# PackageIntegrityValidator direct hostile cases
# ---------------------------------------------------------------------------

def test_valid_package_verifies():
    provenance, store, _leaf, _rk, _rc, manifest = _valid_setup()
    PackageIntegrityValidator.validate_package(provenance, ARTIFACT_BYTES, store, manifest)  # must not raise


def test_altered_artifact_rejected_by_digest_mismatch():
    provenance, store, *_ , manifest = _valid_setup()
    with pytest.raises(PackageDigestMismatchError):
        PackageIntegrityValidator.validate_package(provenance, b"tampered bytes", store, manifest)


def test_wrong_declared_digest_rejected():
    provenance, store, *_ , manifest = _valid_setup()
    bad = dataclasses.replace(provenance, artifact_digest_hex="00" * 32)
    with pytest.raises(PackageDigestMismatchError):
        PackageIntegrityValidator.validate_package(bad, ARTIFACT_BYTES, store, manifest)


def test_forged_signature_rejected():
    provenance, store, _leaf, _rk, _rc, manifest = _valid_setup()
    other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    envelope_digest = canonical_envelope_digest(manifest, provenance.artifact_digest_hex)
    forged_sig = _sign_digest(other_key, envelope_digest)
    bad = dataclasses.replace(provenance, signature=forged_sig)
    with pytest.raises(PackageSignatureInvalidError):
        PackageIntegrityValidator.validate_package(bad, ARTIFACT_BYTES, store, manifest)


def test_malformed_signature_bytes_rejected():
    provenance, store, *_ , manifest = _valid_setup()
    bad = dataclasses.replace(provenance, signature=b"not-a-real-signature-blob")
    with pytest.raises(PackageSignatureInvalidError):
        PackageIntegrityValidator.validate_package(bad, ARTIFACT_BYTES, store, manifest)


# ---------------------------------------------------------------------------
# Hostile-review BLOCKER #2 fix: canonical envelope binding
# ---------------------------------------------------------------------------

def test_mutated_capability_invalidates_signature():
    provenance, store, *_ , manifest = _valid_setup()
    from akaalEngine.extensions.models.capability import CapabilityDeclaration
    mutated_strat = dataclasses.replace(
        manifest.provider_contributions[0].strategies[0],
        capabilities=(CapabilityDeclaration(capability_name="BULK_WRITE", is_supported=True),),
    )
    mutated_prov = dataclasses.replace(manifest.provider_contributions[0], strategies=(mutated_strat,))
    mutated_manifest = dataclasses.replace(manifest, provider_contributions=(mutated_prov,))
    with pytest.raises(PackageSignatureInvalidError):
        PackageIntegrityValidator.validate_package(provenance, ARTIFACT_BYTES, store, mutated_manifest)


def test_mutated_publisher_invalidates_signature():
    provenance, store, *_ , manifest = _valid_setup()
    mutated_manifest = dataclasses.replace(manifest, publisher_id="different-publisher")
    with pytest.raises(PackageSignatureInvalidError):
        PackageIntegrityValidator.validate_package(provenance, ARTIFACT_BYTES, store, mutated_manifest)


def test_mutated_extension_id_invalidates_signature():
    provenance, store, *_ , manifest = _valid_setup()
    mutated_manifest = dataclasses.replace(manifest, extension_id=ExtensionId("ext.different"))
    with pytest.raises(PackageSignatureInvalidError):
        PackageIntegrityValidator.validate_package(provenance, ARTIFACT_BYTES, store, mutated_manifest)


def test_mutated_version_invalidates_signature():
    provenance, store, *_ , manifest = _valid_setup()
    mutated_manifest = dataclasses.replace(manifest, version="9.9.9")
    with pytest.raises(PackageSignatureInvalidError):
        PackageIntegrityValidator.validate_package(provenance, ARTIFACT_BYTES, store, mutated_manifest)


def test_mutated_permission_request_invalidates_signature():
    from akaalEngine.extensions.sandbox.permissions import PermissionRequest
    provenance, store, *_ , manifest = _valid_setup()
    manifest_with_perms = dataclasses.replace(
        manifest, permission_request=PermissionRequest(network_egress_hosts=frozenset({"api.example.com"}))
    )
    # signature was computed against manifest WITHOUT this permission request
    with pytest.raises(PackageSignatureInvalidError):
        PackageIntegrityValidator.validate_package(provenance, ARTIFACT_BYTES, store, manifest_with_perms)


def test_reusing_valid_signature_with_swapped_metadata_only_is_rejected():
    """
    The exact hostile-review scenario: attacker has one validly-signed artifact+signature
    and tries to relabel extension_id/version while keeping the same artifact bytes and
    signature -- must fail because the signature covers the manifest identity too.
    """
    provenance, store, *_ , manifest = _valid_setup(extension_id="ext.original")
    relabeled_provenance = dataclasses.replace(provenance, extension_id="ext.stolen")
    relabeled_manifest = dataclasses.replace(manifest, extension_id=ExtensionId("ext.stolen"))
    with pytest.raises(PackageSignatureInvalidError):
        PackageIntegrityValidator.validate_package(relabeled_provenance, ARTIFACT_BYTES, store, relabeled_manifest)


# ---------------------------------------------------------------------------
# Hostile-review BLOCKER #1 fix: chain policy enforcement
# ---------------------------------------------------------------------------

def test_non_ca_intermediate_cannot_vouch_for_leaf():
    """An intermediate lacking BasicConstraints CA=True must not be usable as an issuer,
    even though its signature over the leaf verifies cryptographically."""
    root_key, root_cert = _make_root()
    # "intermediate" is actually issued as a non-CA leaf-shaped cert
    fake_intermediate_key, fake_intermediate_cert = _make_leaf(
        root_key, root_cert, cn="Fake Non-CA Intermediate", is_ca=False, include_code_signing_eku=False,
    )
    leaf_key, leaf_cert = _make_leaf(
        fake_intermediate_key, fake_intermediate_cert, cn="Leaf Signed By Non-CA",
    )
    manifest = _manifest("ext.pkg")
    digest_hex = hashlib.sha256(ARTIFACT_BYTES).hexdigest()
    envelope_digest = canonical_envelope_digest(manifest, digest_hex)
    sig = _sign_digest(leaf_key, envelope_digest)
    provenance = PackageProvenance(
        extension_id="ext.pkg", version="1.0.0", artifact_digest_hex=digest_hex,
        digest_algorithm="sha256", signature=sig, signer_certificate_pem=_pem(leaf_cert),
        intermediate_certificates_pem=(_pem(fake_intermediate_cert),),
    )
    store = PublisherTrustStore()
    store.register_trust_root("acme-root", _pem(root_cert))
    with pytest.raises(PackageCertificateInvalidError):
        PackageIntegrityValidator.validate_package(provenance, ARTIFACT_BYTES, store, manifest)


def test_intermediate_without_key_cert_sign_is_rejected():
    root_key, root_cert = _make_root()
    # CA=True but KeyUsage explicitly withholds keyCertSign
    int_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    int_subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Intermediate No CertSign")])
    intermediate_cert = (
        x509.CertificateBuilder()
        .subject_name(int_subject).issuer_name(root_cert.subject).public_key(int_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(timezone.utc) - timedelta(days=1))
        .not_valid_after(datetime.now(timezone.utc) + timedelta(days=365))
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=True, content_commitment=False, key_encipherment=False,
                data_encipherment=False, key_agreement=False, key_cert_sign=False,
                crl_sign=False, encipher_only=False, decipher_only=False,
            ),
            critical=True,
        )
        .sign(root_key, hashes.SHA256())
    )
    leaf_key, leaf_cert = _make_leaf(int_key, intermediate_cert, cn="Leaf Under Weak Intermediate")
    manifest = _manifest("ext.pkg")
    digest_hex = hashlib.sha256(ARTIFACT_BYTES).hexdigest()
    envelope_digest = canonical_envelope_digest(manifest, digest_hex)
    sig = _sign_digest(leaf_key, envelope_digest)
    provenance = PackageProvenance(
        extension_id="ext.pkg", version="1.0.0", artifact_digest_hex=digest_hex,
        digest_algorithm="sha256", signature=sig, signer_certificate_pem=_pem(leaf_cert),
        intermediate_certificates_pem=(_pem(intermediate_cert),),
    )
    store = PublisherTrustStore()
    store.register_trust_root("acme-root", _pem(root_cert))
    with pytest.raises(PackageCertificateInvalidError):
        PackageIntegrityValidator.validate_package(provenance, ARTIFACT_BYTES, store, manifest)


def test_leaf_with_ca_true_is_rejected_even_if_otherwise_valid():
    root_key, root_cert = _make_root()
    leaf_key, leaf_cert = _make_leaf(root_key, root_cert, is_ca=True)  # leaf mistakenly marked as CA
    manifest = _manifest("ext.pkg")
    digest_hex = hashlib.sha256(ARTIFACT_BYTES).hexdigest()
    envelope_digest = canonical_envelope_digest(manifest, digest_hex)
    sig = _sign_digest(leaf_key, envelope_digest)
    provenance = PackageProvenance(
        extension_id="ext.pkg", version="1.0.0", artifact_digest_hex=digest_hex,
        digest_algorithm="sha256", signature=sig, signer_certificate_pem=_pem(leaf_cert),
    )
    store = PublisherTrustStore()
    store.register_trust_root("acme-root", _pem(root_cert))
    with pytest.raises(PackageCertificateInvalidError):
        PackageIntegrityValidator.validate_package(provenance, ARTIFACT_BYTES, store, manifest)


def test_leaf_with_wrong_extended_key_usage_purpose_is_rejected():
    root_key, root_cert = _make_root()
    leaf_key, leaf_cert = _make_leaf(
        root_key, root_cert, eku_purpose=ExtendedKeyUsageOID.SERVER_AUTH,  # TLS-server cert, not code-signing
    )
    manifest = _manifest("ext.pkg")
    digest_hex = hashlib.sha256(ARTIFACT_BYTES).hexdigest()
    envelope_digest = canonical_envelope_digest(manifest, digest_hex)
    sig = _sign_digest(leaf_key, envelope_digest)
    provenance = PackageProvenance(
        extension_id="ext.pkg", version="1.0.0", artifact_digest_hex=digest_hex,
        digest_algorithm="sha256", signature=sig, signer_certificate_pem=_pem(leaf_cert),
    )
    store = PublisherTrustStore()
    store.register_trust_root("acme-root", _pem(root_cert))
    with pytest.raises(PackageCertificateInvalidError):
        PackageIntegrityValidator.validate_package(provenance, ARTIFACT_BYTES, store, manifest)


def test_leaf_without_eku_extension_is_accepted():
    """Absence of the EKU extension entirely is accepted (common for real code-signing certs)."""
    root_key, root_cert = _make_root()
    leaf_key, leaf_cert = _make_leaf(root_key, root_cert, include_code_signing_eku=False)
    manifest = _manifest("ext.pkg")
    digest_hex = hashlib.sha256(ARTIFACT_BYTES).hexdigest()
    envelope_digest = canonical_envelope_digest(manifest, digest_hex)
    sig = _sign_digest(leaf_key, envelope_digest)
    provenance = PackageProvenance(
        extension_id="ext.pkg", version="1.0.0", artifact_digest_hex=digest_hex,
        digest_algorithm="sha256", signature=sig, signer_certificate_pem=_pem(leaf_cert),
    )
    store = PublisherTrustStore()
    store.register_trust_root("acme-root", _pem(root_cert))
    PackageIntegrityValidator.validate_package(provenance, ARTIFACT_BYTES, store, manifest)  # must not raise


def test_weak_signature_algorithm_check_rejects_sha1_and_md5():
    """
    The `cryptography` library itself (v50.1) now refuses to even construct a SHA-1-signed
    certificate via its builder API -- UnsupportedAlgorithm at sign() time -- confirming the
    ecosystem already blocks this at the tooling level. That doesn't mean our own guard is
    unreachable: a certificate parsed from an externally-supplied PEM (produced by some other,
    non-`cryptography`-based, non-policy-enforcing tool) could still carry a weak algorithm, so
    _check_signature_algorithm_strength must independently reject it. Tested directly against
    the check function with a minimal stand-in exposing exactly the attributes it reads,
    since constructing a real weak-signed x509.Certificate object is no longer possible
    through this library's own API.
    """
    class _FakeSubject:
        def rfc4514_string(self):
            return "CN=Fake"

    class _FakeCertWithWeakAlgo:
        subject = _FakeSubject()
        def __init__(self, algo):
            self.signature_hash_algorithm = algo

    for weak_algo in (hashes.SHA1(), hashes.MD5(), None):
        with pytest.raises(PackageCertificateInvalidError):
            PackageIntegrityValidator._check_signature_algorithm_strength(_FakeCertWithWeakAlgo(weak_algo))

    # Sanity: a real, strong-algorithm certificate must NOT raise.
    _root_key, root_cert = _make_root()
    PackageIntegrityValidator._check_signature_algorithm_strength(root_cert)


def test_path_length_constraint_violation_is_rejected():
    """A path_length=0 intermediate may not be followed by any further intermediate."""
    root_key, root_cert = _make_root()
    int1_key, int1_cert = _make_leaf(root_key, root_cert, cn="Intermediate1", is_ca=True, include_code_signing_eku=False)
    # Force path_length=0 on int1 via direct construction (must forbid a further intermediate below it)
    int1_key2 = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    int1_subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Intermediate PathLen0")])
    int1_cert2 = (
        x509.CertificateBuilder()
        .subject_name(int1_subject).issuer_name(root_cert.subject).public_key(int1_key2.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(timezone.utc) - timedelta(days=1))
        .not_valid_after(datetime.now(timezone.utc) + timedelta(days=365))
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=False, content_commitment=False, key_encipherment=False,
                data_encipherment=False, key_agreement=False, key_cert_sign=True,
                crl_sign=True, encipher_only=False, decipher_only=False,
            ),
            critical=True,
        )
        .sign(root_key, hashes.SHA256())
    )
    int2_key, int2_cert = _make_leaf(int1_key2, int1_cert2, cn="Intermediate2 (should be disallowed below path_length=0)", is_ca=True, include_code_signing_eku=False)
    leaf_key, leaf_cert = _make_leaf(int2_key, int2_cert, cn="Leaf Beyond Path Length")
    manifest = _manifest("ext.pkg")
    digest_hex = hashlib.sha256(ARTIFACT_BYTES).hexdigest()
    envelope_digest = canonical_envelope_digest(manifest, digest_hex)
    sig = _sign_digest(leaf_key, envelope_digest)
    provenance = PackageProvenance(
        extension_id="ext.pkg", version="1.0.0", artifact_digest_hex=digest_hex,
        digest_algorithm="sha256", signature=sig, signer_certificate_pem=_pem(leaf_cert),
        intermediate_certificates_pem=(_pem(int2_cert), _pem(int1_cert2)),
    )
    store = PublisherTrustStore()
    store.register_trust_root("acme-root", _pem(root_cert))
    with pytest.raises(PackageCertificateInvalidError):
        PackageIntegrityValidator.validate_package(provenance, ARTIFACT_BYTES, store, manifest)


# ---------------------------------------------------------------------------
# Trust root / revocation hostile cases
# ---------------------------------------------------------------------------

def test_unknown_publisher_no_trust_roots_registered():
    provenance, _store, *_ , manifest = _valid_setup()
    empty_store = PublisherTrustStore()
    with pytest.raises(PackageTrustRootUnknownError):
        PackageIntegrityValidator.validate_package(provenance, ARTIFACT_BYTES, empty_store, manifest)


def test_untrusted_issuer_different_root_registered():
    provenance, _store, *_ , manifest = _valid_setup()
    _other_root_key, other_root_cert = _make_root(cn="A Different, Unrelated Root")
    wrong_store = PublisherTrustStore()
    wrong_store.register_trust_root("other-root", _pem(other_root_cert))
    with pytest.raises(PackageTrustRootUnknownError):
        PackageIntegrityValidator.validate_package(provenance, ARTIFACT_BYTES, wrong_store, manifest)


def test_expired_signer_certificate_rejected():
    root_key, root_cert = _make_root()
    leaf_key, leaf_cert = _make_leaf(root_key, root_cert, not_after_days=-1, not_before_days=-30)
    manifest = _manifest("ext.pkg")
    digest_hex = hashlib.sha256(ARTIFACT_BYTES).hexdigest()
    envelope_digest = canonical_envelope_digest(manifest, digest_hex)
    sig = _sign_digest(leaf_key, envelope_digest)
    provenance = PackageProvenance(
        extension_id="ext.pkg", version="1.0.0", artifact_digest_hex=digest_hex,
        digest_algorithm="sha256", signature=sig, signer_certificate_pem=_pem(leaf_cert),
    )
    store = PublisherTrustStore()
    store.register_trust_root("acme-root", _pem(root_cert))
    with pytest.raises(PackageCertificateInvalidError):
        PackageIntegrityValidator.validate_package(provenance, ARTIFACT_BYTES, store, manifest)


def test_not_yet_valid_signer_certificate_rejected():
    root_key, root_cert = _make_root()
    leaf_key, leaf_cert = _make_leaf(root_key, root_cert, not_after_days=365, not_before_days=30)
    manifest = _manifest("ext.pkg")
    digest_hex = hashlib.sha256(ARTIFACT_BYTES).hexdigest()
    envelope_digest = canonical_envelope_digest(manifest, digest_hex)
    sig = _sign_digest(leaf_key, envelope_digest)
    provenance = PackageProvenance(
        extension_id="ext.pkg", version="1.0.0", artifact_digest_hex=digest_hex,
        digest_algorithm="sha256", signature=sig, signer_certificate_pem=_pem(leaf_cert),
    )
    store = PublisherTrustStore()
    store.register_trust_root("acme-root", _pem(root_cert))
    with pytest.raises(PackageCertificateInvalidError):
        PackageIntegrityValidator.validate_package(provenance, ARTIFACT_BYTES, store, manifest)


def test_revoked_signer_certificate_rejected():
    provenance, store, leaf_cert, _rk, _rc, manifest = _valid_setup()
    store.revoke_signer_serial(leaf_cert.serial_number)
    with pytest.raises(PackageCertificateRevokedError):
        PackageIntegrityValidator.validate_package(provenance, ARTIFACT_BYTES, store, manifest)


def test_revoked_trust_root_no_longer_verifies():
    provenance, store, *_ , manifest = _valid_setup()
    store.revoke_trust_root("acme-root")
    with pytest.raises(PackageTrustRootUnknownError):
        PackageIntegrityValidator.validate_package(provenance, ARTIFACT_BYTES, store, manifest)


def test_malformed_certificate_pem_rejected():
    provenance, store, *_ , manifest = _valid_setup()
    bad = dataclasses.replace(provenance, signer_certificate_pem="-----BEGIN CERTIFICATE-----\nnot-real-data\n-----END CERTIFICATE-----")
    with pytest.raises(PackageCertificateInvalidError):
        PackageIntegrityValidator.validate_package(bad, ARTIFACT_BYTES, store, manifest)


def test_self_signed_leaf_not_pinned_is_rejected():
    """A self-signed cert with no chain to, and not itself pinned as, a registered trust root is rejected."""
    self_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Self-Signed Impersonator")])
    self_signed_cert = (
        x509.CertificateBuilder()
        .subject_name(subject).issuer_name(subject).public_key(self_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(timezone.utc) - timedelta(days=1))
        .not_valid_after(datetime.now(timezone.utc) + timedelta(days=365))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .sign(self_key, hashes.SHA256())
    )
    manifest = _manifest("ext.pkg")
    digest_hex = hashlib.sha256(ARTIFACT_BYTES).hexdigest()
    envelope_digest = canonical_envelope_digest(manifest, digest_hex)
    sig = _sign_digest(self_key, envelope_digest)
    provenance = PackageProvenance(
        extension_id="ext.pkg", version="1.0.0", artifact_digest_hex=digest_hex,
        digest_algorithm="sha256", signature=sig, signer_certificate_pem=_pem(self_signed_cert),
    )
    _root_key, root_cert = _make_root()
    store = PublisherTrustStore()
    store.register_trust_root("acme-root", _pem(root_cert))
    with pytest.raises(PackageTrustRootUnknownError):
        PackageIntegrityValidator.validate_package(provenance, ARTIFACT_BYTES, store, manifest)


def test_explicitly_pinned_leaf_certificate_is_a_valid_trust_model():
    """Direct certificate pinning (operator explicitly trusts one exact cert, not a CA chain) is honored."""
    provenance, _store, leaf_cert, _rk, _rc, manifest = _valid_setup()
    pinned_store = PublisherTrustStore()
    pinned_store.register_trust_root("pinned-leaf", _pem(leaf_cert))
    PackageIntegrityValidator.validate_package(provenance, ARTIFACT_BYTES, pinned_store, manifest)  # must not raise


def test_ec_signer_key_supported():
    root_key, root_cert = _make_root()
    ec_key = ec.generate_private_key(ec.SECP256R1())
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "AKAAL EC Publisher")])
    leaf_cert = (
        x509.CertificateBuilder()
        .subject_name(subject).issuer_name(root_cert.subject).public_key(ec_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(timezone.utc) - timedelta(days=1))
        .not_valid_after(datetime.now(timezone.utc) + timedelta(days=365))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.CODE_SIGNING]), critical=False)
        .sign(root_key, hashes.SHA256())
    )
    manifest = _manifest("ext.pkg")
    digest_hex = hashlib.sha256(ARTIFACT_BYTES).hexdigest()
    envelope_digest = canonical_envelope_digest(manifest, digest_hex)
    sig = _sign_digest(ec_key, envelope_digest)
    provenance = PackageProvenance(
        extension_id="ext.pkg", version="1.0.0", artifact_digest_hex=digest_hex,
        digest_algorithm="sha256", signature=sig, signer_certificate_pem=_pem(leaf_cert),
    )
    store = PublisherTrustStore()
    store.register_trust_root("acme-root", _pem(root_cert))
    PackageIntegrityValidator.validate_package(provenance, ARTIFACT_BYTES, store, manifest)  # must not raise


# ---------------------------------------------------------------------------
# Registration-gate integration: THIRD_PARTY_PACKAGE origin must be fail-closed
# ---------------------------------------------------------------------------

def test_third_party_registration_without_any_provenance_rejected():
    reg = ExtensionRegistry()
    manifest = _manifest("ext.unsigned")
    with pytest.raises(PackageProvenanceMissingError):
        reg.register_extension(manifest)


def test_third_party_registration_with_mismatched_identity_rejected():
    reg = ExtensionRegistry()
    manifest = _manifest("ext.mismatch", version="1.0.0")
    provenance, store, *_ , _other_manifest = _valid_setup(extension_id="ext.DIFFERENT", version="1.0.0")
    with pytest.raises(PackageProvenanceMissingError):
        reg.register_extension(
            manifest,
            package_provenance=provenance,
            package_artifact_bytes=ARTIFACT_BYTES,
            trust_store=store,
        )


def test_third_party_registration_with_forged_signature_rejected():
    reg = ExtensionRegistry()
    manifest = _manifest("ext.forged")
    provenance, store, *_ = _valid_setup(extension_id="ext.forged", version="1.0.0")
    other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    envelope_digest = canonical_envelope_digest(manifest, provenance.artifact_digest_hex)
    forged = dataclasses.replace(provenance, signature=_sign_digest(other_key, envelope_digest))
    with pytest.raises(PackageSignatureInvalidError):
        reg.register_extension(
            manifest,
            package_provenance=forged,
            package_artifact_bytes=ARTIFACT_BYTES,
            trust_store=store,
        )


def test_third_party_registration_with_valid_provenance_succeeds():
    reg = ExtensionRegistry()
    provenance, store, *_ , manifest = _valid_setup(extension_id="ext.signed.ok", version="1.0.0")
    manifest = dataclasses.replace(manifest, extension_id=ExtensionId("ext.signed.ok"))
    snap = reg.register_extension(
        manifest,
        package_provenance=provenance,
        package_artifact_bytes=ARTIFACT_BYTES,
        trust_store=store,
    )
    assert snap.get_extension(ExtensionId("ext.signed.ok")) == manifest


def test_hijack_of_registered_provider_rejected_before_supply_chain_is_even_consulted():
    """
    Ownership/hijack protection must be independent of signing status: a rogue THIRD_PARTY_PACKAGE
    attempting to take over an existing provider is rejected even with zero provenance supplied,
    proving the ownership gate is not bypassable merely by omitting or forging a signature.
    """
    reg = ExtensionRegistry()
    default_contract_registry.register_contract(
        AuthorityContractDefinition(authority_id=AuthorityId("transport"), contract_version="1.0.0", description="t")
    )
    strat = StrategyContribution(
        strategy_id=StrategyId("shared-prov-strat"),
        authority_id=AuthorityId("transport"),
        provider_id=ProviderId("shared-prov"),
        contract_version_range=CompatibilityRange("*"),
        strategy_factory=lambda: object(),
    )
    prov = ProviderContribution(
        provider_id=ProviderId("shared-prov"), vendor_name="V", display_name="P",
        family="relational", strategies=(strat,),
    )
    builtin_manifest = ExtensionManifest(
        extension_id=ExtensionId("ext.builtin.hijack"), version="1.0.0", display_name="Builtin",
        engine_version_range=CompatibilityRange(">=1.0.0"), origin=ExtensionOrigin.BUILTIN,
        provider_contributions=(prov,),
    )
    reg.register_extension(builtin_manifest)

    rogue_prov = ProviderContribution(
        provider_id=ProviderId("shared-prov"), vendor_name="Rogue", display_name="Rogue",
        family="relational", strategies=(strat,),
    )
    rogue_manifest = ExtensionManifest(
        extension_id=ExtensionId("ext.rogue.hijack"), version="1.0.0", display_name="Rogue",
        engine_version_range=CompatibilityRange(">=1.0.0"), origin=ExtensionOrigin.THIRD_PARTY_PACKAGE,
        provider_contributions=(rogue_prov,),
    )
    from akaalEngine.extensions.errors.taxonomy import ExtensionConflictError
    with pytest.raises(ExtensionConflictError):
        reg.register_extension(rogue_manifest, allow_replace=False)
