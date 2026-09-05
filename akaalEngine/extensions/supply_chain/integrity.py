"""
akaalEngine.extensions.supply_chain.integrity
==============================================
Real cryptographic verification of third-party extension package provenance:
artifact digest integrity, X.509 signer-chain validation to a registered publisher
trust root (with real policy enforcement -- BasicConstraints, KeyUsage, ExtendedKeyUsage,
algorithm strength, path length -- not just "does a signature verify"), revocation, and
signature verification over the FULL canonical manifest envelope (not merely the artifact
digest) so that extension_id/version/publisher/permissions/capabilities cannot be swapped
after signing.

Fails closed at every stage. A package that cannot be fully verified is never admitted --
there is no partial-trust or best-effort admission path here.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import List, Optional, Sequence

from cryptography import x509
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec, padding, rsa, utils
from cryptography.x509.oid import ExtendedKeyUsageOID

from akaalEngine.extensions.errors.taxonomy import (
    PackageCertificateInvalidError,
    PackageCertificateRevokedError,
    PackageDigestMismatchError,
    PackageSignatureInvalidError,
    PackageTrustRootUnknownError,
)
from akaalEngine.extensions.models.extension import ExtensionManifest
from akaalEngine.extensions.models.provenance import PackageProvenance
from akaalEngine.extensions.supply_chain.canonical import canonical_envelope_digest
from akaalEngine.extensions.supply_chain.trust_store import PublisherTrustStore

# Explicit allow-list. Anything not in this set (MD5, SHA-1, or an unrecognized algorithm)
# is rejected -- no silent weak-algorithm downgrade for chain-certificate signatures.
_ACCEPTABLE_CERT_SIGNATURE_ALGORITHMS = (hashes.SHA256, hashes.SHA384, hashes.SHA512)


class PackageIntegrityValidator:
    """Stateless verification of a package artifact against its provenance, manifest, and a trust store."""

    @staticmethod
    def compute_digest(artifact_bytes: bytes) -> str:
        return hashlib.sha256(artifact_bytes).hexdigest()

    @classmethod
    def validate_package(
        cls,
        provenance: PackageProvenance,
        artifact_bytes: bytes,
        trust_store: PublisherTrustStore,
        manifest: ExtensionManifest,
        now: datetime = None,
    ) -> None:
        """
        Verifies, in order:
          1. artifact digest matches the declared provenance digest
          2. the signer certificate (and any intermediates) parse
          3. the signer certificate chains to a registered trust anchor via real
             signature-verified, policy-enforced walk (BasicConstraints CA flag on every
             issuer, KeyUsage keyCertSign on every issuer, ExtendedKeyUsage code-signing
             purpose on the leaf signer, no weak signature algorithms, path-length limits,
             temporal validity at every hop)
          4. no certificate in the chain has been revoked
          5. the declared signature verifies over the SHA-256 digest of the CANONICAL
             manifest envelope (extension_id + version + publisher_id + permissions +
             capabilities + provider/strategy identities + artifact digest) -- not the bare
             artifact digest alone, so none of those fields can be swapped post-signing
             without invalidating the signature.

        Raises a typed PackageEngineException subclass on the first failure. Never returns a
        partial-success value -- a return with no exception means full verification succeeded.
        """
        now = now or datetime.now(timezone.utc)

        # 1. Digest integrity
        computed = cls.compute_digest(artifact_bytes)
        if computed.lower() != provenance.artifact_digest_hex.lower():
            raise PackageDigestMismatchError(
                f"Artifact digest mismatch for extension '{provenance.extension_id}' "
                f"version '{provenance.version}': computed={computed}, declared={provenance.artifact_digest_hex}."
            )

        # 2. Parse signer + intermediate certificates
        signer_cert = cls._parse_certificate(provenance.signer_certificate_pem, label="signer")
        intermediates = [
            cls._parse_certificate(pem, label="intermediate")
            for pem in provenance.intermediate_certificates_pem
        ]

        # 2b. Leaf-specific policy: must be a code-signing-eligible certificate, must not
        # itself be a CA (a CA certificate masquerading as a package signer is rejected --
        # separates "authorized to vouch for other certs" from "authorized to sign packages").
        cls._check_leaf_policy(signer_cert)

        # 3. Policy-enforced chain validation to a registered trust anchor
        chain = [signer_cert] + intermediates
        anchor = cls._verify_chain_to_trust_anchor(chain, trust_store, now)

        # 4. Revocation check across the whole verified chain
        for cert in chain:
            if trust_store.is_serial_revoked(cert.serial_number):
                raise PackageCertificateRevokedError(
                    f"Signer certificate chain for extension '{provenance.extension_id}' contains a "
                    f"revoked certificate (serial={cert.serial_number})."
                )
        if trust_store.is_serial_revoked(anchor.serial_number):
            raise PackageCertificateRevokedError(
                f"Trust anchor for extension '{provenance.extension_id}' has been revoked "
                f"(serial={anchor.serial_number})."
            )

        # 5. Signature verification over the canonical envelope digest (binds identity,
        # version, publisher, permissions, capabilities, providers/strategies, and digest).
        envelope_digest = canonical_envelope_digest(manifest, computed)
        cls._verify_signature(signer_cert, provenance.signature, envelope_digest)

    @staticmethod
    def _parse_certificate(pem: str, label: str) -> x509.Certificate:
        try:
            return x509.load_pem_x509_certificate(pem.encode("utf-8"), default_backend())
        except Exception as exc:
            raise PackageCertificateInvalidError(f"Malformed {label} certificate: {exc}") from exc

    @staticmethod
    def _check_temporal_validity(cert: x509.Certificate, now: datetime, label: str) -> None:
        not_before = cert.not_valid_before_utc if hasattr(cert, "not_valid_before_utc") else cert.not_valid_before.replace(tzinfo=timezone.utc)
        not_after = cert.not_valid_after_utc if hasattr(cert, "not_valid_after_utc") else cert.not_valid_after.replace(tzinfo=timezone.utc)
        if now < not_before:
            raise PackageCertificateInvalidError(f"{label} certificate is not yet valid (not_before={not_before}).")
        if now > not_after:
            raise PackageCertificateInvalidError(f"{label} certificate has expired (not_after={not_after}).")

    @staticmethod
    def _get_basic_constraints(cert: x509.Certificate) -> Optional[x509.BasicConstraints]:
        try:
            return cert.extensions.get_extension_for_class(x509.BasicConstraints).value
        except x509.ExtensionNotFound:
            return None

    @staticmethod
    def _get_key_usage(cert: x509.Certificate) -> Optional[x509.KeyUsage]:
        try:
            return cert.extensions.get_extension_for_class(x509.KeyUsage).value
        except x509.ExtensionNotFound:
            return None

    @staticmethod
    def _get_extended_key_usage(cert: x509.Certificate) -> Optional[x509.ExtendedKeyUsage]:
        try:
            return cert.extensions.get_extension_for_class(x509.ExtendedKeyUsage).value
        except x509.ExtensionNotFound:
            return None

    @classmethod
    def _check_leaf_policy(cls, leaf: x509.Certificate) -> None:
        """
        The package-signing leaf certificate must not itself be a CA (BasicConstraints
        ca=True on a leaf is a sign of misconfiguration/attack -- a CA cert should not
        double as a package-signing identity), and if it declares an ExtendedKeyUsage
        extension, code-signing (or anyExtendedKeyUsage) must be among the declared
        purposes -- rejecting e.g. a TLS-server-only certificate repurposed for signing.
        Absence of the EKU extension is accepted (many code-signing certs omit it), but
        an EKU that explicitly excludes code signing is rejected.
        """
        bc = cls._get_basic_constraints(leaf)
        if bc is not None and bc.ca:
            raise PackageCertificateInvalidError(
                "Signer certificate has BasicConstraints CA=True; a CA certificate may not "
                "be used directly as a package-signing identity."
            )
        eku = cls._get_extended_key_usage(leaf)
        if eku is not None:
            allowed = set(eku)
            if ExtendedKeyUsageOID.CODE_SIGNING not in allowed and ExtendedKeyUsageOID.ANY_EXTENDED_KEY_USAGE not in allowed:
                raise PackageCertificateInvalidError(
                    "Signer certificate's ExtendedKeyUsage does not include code signing."
                )

    @classmethod
    def _check_issuer_policy(cls, issuer: x509.Certificate, *, is_trust_anchor: bool) -> None:
        """
        A certificate used to VOUCH FOR another certificate (an intermediate, or a
        self-signed root acting as issuer) must carry BasicConstraints CA=True -- a
        non-CA certificate (e.g. an ordinary leaf, even a validly-issued one) cannot be
        used to sign other certificates, no matter how its signature checks out
        mathematically. Self-signed trust anchors registered directly via
        register_trust_root (pinned exact-certificate trust) are exempt from the CA-flag
        requirement -- pinning an exact certificate is an explicit administrative act of
        trust in that one certificate, not a delegation of issuing authority.
        """
        if is_trust_anchor:
            return
        bc = cls._get_basic_constraints(issuer)
        if bc is None or not bc.ca:
            raise PackageCertificateInvalidError(
                f"Certificate '{issuer.subject.rfc4514_string()}' lacks BasicConstraints "
                f"CA=True and cannot be used to vouch for another certificate."
            )
        ku = cls._get_key_usage(issuer)
        if ku is not None and not ku.key_cert_sign:
            raise PackageCertificateInvalidError(
                f"Certificate '{issuer.subject.rfc4514_string()}' has KeyUsage present but "
                f"without keyCertSign; it is not authorized to sign other certificates."
            )

    @staticmethod
    def _check_signature_algorithm_strength(cert: x509.Certificate) -> None:
        algo = cert.signature_hash_algorithm
        if algo is None or not isinstance(algo, _ACCEPTABLE_CERT_SIGNATURE_ALGORITHMS):
            algo_name = type(algo).__name__ if algo is not None else "unknown"
            raise PackageCertificateInvalidError(
                f"Certificate '{cert.subject.rfc4514_string()}' uses a disallowed or weak "
                f"signature algorithm '{algo_name}' (only SHA-256/384/512 are accepted)."
            )

    @classmethod
    def _verify_chain_to_trust_anchor(
        cls,
        chain: List[x509.Certificate],
        trust_store: PublisherTrustStore,
        now: datetime,
    ) -> x509.Certificate:
        """
        Walks signer -> intermediates -> trust anchor, verifying at every hop:
          - the subject's signature was produced by the candidate issuer's public key
          - the issuer (unless it's a directly-pinned trust anchor) has BasicConstraints
            CA=True and, if present, KeyUsage.keyCertSign
          - the issuer's own signature algorithm is not weak/disallowed
          - path-length constraints (BasicConstraints.path_length) are honored
          - every hop is temporally valid
        Returns the trust anchor certificate that terminated the chain.
        """
        anchors_by_subject = {}
        for anchor in trust_store.get_trust_anchors():
            anchors_by_subject.setdefault(anchor.subject.public_bytes(), []).append(anchor)

        if not anchors_by_subject:
            raise PackageTrustRootUnknownError(
                "No publisher trust roots are registered; cannot verify any package signer chain."
            )

        current = chain[0]
        cls._check_temporal_validity(current, now, label="signer")
        cls._check_signature_algorithm_strength(current)
        remaining = chain[1:]

        visited_fingerprints = set()
        intermediates_traversed = 0
        while True:
            current_fp = current.fingerprint(hashes.SHA256())
            if current_fp in visited_fingerprints:
                raise PackageCertificateInvalidError("Certificate chain contains a cycle.")
            visited_fingerprints.add(current_fp)

            # Is current itself a directly-pinned trust anchor? (exact-certificate pinning,
            # exempt from CA-flag requirement -- see _check_issuer_policy docstring.)
            candidate_anchors = anchors_by_subject.get(current.subject.public_bytes(), [])
            for anchor in candidate_anchors:
                if anchor.fingerprint(hashes.SHA256()) == current_fp:
                    return anchor

            # Find the issuer: prefer an explicit intermediate, else a registered trust anchor.
            issuer_candidates: Sequence[x509.Certificate] = [
                c for c in remaining if c.subject.public_bytes() == current.issuer.public_bytes()
            ]
            issuer_is_pinned_anchor = False
            if not issuer_candidates:
                issuer_candidates = anchors_by_subject.get(current.issuer.public_bytes(), [])
                issuer_is_pinned_anchor = True

            if not issuer_candidates:
                raise PackageTrustRootUnknownError(
                    f"Certificate chain does not terminate at any registered trust root "
                    f"(no issuer found for subject '{current.subject.rfc4514_string()}')."
                )

            verified_issuer = None
            for candidate in issuer_candidates:
                if cls._signature_verifies(subject=current, issuer=candidate):
                    verified_issuer = candidate
                    break

            if verified_issuer is None:
                raise PackageCertificateInvalidError(
                    f"Signature verification failed while walking chain from subject "
                    f"'{current.subject.rfc4514_string()}' to a candidate issuer."
                )

            # Is the verified issuer itself a registered (possibly pinned) trust anchor?
            anchor_match = next(
                (a for a in anchors_by_subject.get(verified_issuer.subject.public_bytes(), [])
                 if a.fingerprint(hashes.SHA256()) == verified_issuer.fingerprint(hashes.SHA256())),
                None,
            )
            is_pinned_exact_match = anchor_match is not None and issuer_is_pinned_anchor

            cls._check_issuer_policy(verified_issuer, is_trust_anchor=is_pinned_exact_match)
            cls._check_signature_algorithm_strength(verified_issuer)

            if anchor_match is not None:
                return anchor_match

            # Path-length enforcement: BasicConstraints.path_length on an intermediate caps
            # how many FURTHER intermediate certificates may appear below it in the chain
            # (i.e. how many more times its authority may be delegated downward from itself).
            bc = cls._get_basic_constraints(verified_issuer)
            if bc is not None and bc.path_length is not None and intermediates_traversed > bc.path_length:
                raise PackageCertificateInvalidError(
                    f"Certificate chain violates path length constraint of "
                    f"'{verified_issuer.subject.rfc4514_string()}' (path_length={bc.path_length})."
                )
            intermediates_traversed += 1

            cls._check_temporal_validity(verified_issuer, now, label="intermediate")
            remaining = [c for c in remaining if c is not verified_issuer]
            current = verified_issuer

    @staticmethod
    def _signature_verifies(subject: x509.Certificate, issuer: x509.Certificate) -> bool:
        issuer_public_key = issuer.public_key()
        try:
            if isinstance(issuer_public_key, rsa.RSAPublicKey):
                issuer_public_key.verify(
                    subject.signature,
                    subject.tbs_certificate_bytes,
                    padding.PKCS1v15(),
                    subject.signature_hash_algorithm,
                )
            elif isinstance(issuer_public_key, ec.EllipticCurvePublicKey):
                issuer_public_key.verify(
                    subject.signature,
                    subject.tbs_certificate_bytes,
                    ec.ECDSA(subject.signature_hash_algorithm),
                )
            else:
                return False
            return True
        except InvalidSignature:
            return False

    @staticmethod
    def _verify_signature(signer_cert: x509.Certificate, signature: bytes, digest: bytes) -> None:
        """
        Verifies `signature` was produced over the raw pre-computed `digest` bytes (the
        SHA-256 digest of the canonical manifest envelope) -- not over the digest re-hashed
        again. Uses `Prehashed` so the digest is treated as-is, matching how a real signer
        would sign it.
        """
        public_key = signer_cert.public_key()
        try:
            if isinstance(public_key, rsa.RSAPublicKey):
                public_key.verify(
                    signature,
                    digest,
                    padding.PKCS1v15(),
                    utils.Prehashed(hashes.SHA256()),
                )
            elif isinstance(public_key, ec.EllipticCurvePublicKey):
                public_key.verify(signature, digest, ec.ECDSA(utils.Prehashed(hashes.SHA256())))
            else:
                raise PackageSignatureInvalidError(
                    f"Unsupported signer public key type: {type(public_key).__name__}."
                )
        except InvalidSignature as exc:
            raise PackageSignatureInvalidError(
                "Package signature does not verify against the signer certificate's public key "
                "over the canonical manifest envelope."
            ) from exc
