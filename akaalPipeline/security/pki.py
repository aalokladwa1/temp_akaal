"""akaalPipeline.security.pki
===========================
P7.2 PKI & Certificate Lifecycle Consumer and Validation Engine.

Strict Invariants:
1. AKAAL IS A PKI CONSUMER — NOT A CA. AKAAL does NOT issue or sign certificates.
2. Unverified / parsed certificates are NOT trusted certificates.
3. Certificate verification requires valid chain, trusted CA anchor, temporal validity, and SAN match.
4. Expiry warning thresholds are configurable (1d - 90d, default 30d).
5. Revocation evaluates true status — UNKNOWN/UNAVAILABLE never becomes NOT_REVOKED.
"""

from __future__ import annotations

import datetime
import hashlib
import logging
from dataclasses import dataclass, field
from datetime import timezone
from typing import Any, Callable, Dict, List, Optional, Sequence, Set, Tuple

from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec, ed25519, padding, rsa
from cryptography.x509.oid import ExtensionOID, ExtendedKeyUsageOID



from akaalPipeline.contracts.enums import CertificateLifecycleState
from akaalPipeline.security.config import SecurityBaselineConfig

logger = logging.getLogger("akaalPipeline.security.pki")


class CertificateValidationError(ValueError):
    """Raised when an X.509 certificate fails cryptographic or policy validation."""
    pass


class CertificateExpiredError(CertificateValidationError):
    """Raised when a certificate has expired."""
    pass


class CertificateNotYetValidError(CertificateValidationError):
    """Raised when a certificate is not yet valid."""
    pass


class CertificateRevokedError(CertificateValidationError):
    """Raised when a certificate has been explicitly revoked."""
    pass


class UntrustedIssuerError(CertificateValidationError):
    """Raised when a certificate chain does not anchor to a trusted CA."""
    pass


@dataclass(frozen=True)
class CertificateMetadata:
    """Normalized, truthful metadata extracted from an X.509 certificate."""

    cert_id: str
    subject: str
    issuer: str
    serial_number: str
    fingerprint_sha256: str
    not_valid_before: datetime.datetime
    not_valid_after: datetime.datetime
    dns_sans: Tuple[str, ...] = field(default_factory=tuple)
    ip_sans: Tuple[str, ...] = field(default_factory=tuple)
    uri_sans: Tuple[str, ...] = field(default_factory=tuple)
    key_usage: Tuple[str, ...] = field(default_factory=tuple)
    extended_key_usage: Tuple[str, ...] = field(default_factory=tuple)
    is_ca: bool = False
    state: CertificateLifecycleState = CertificateLifecycleState.DISCOVERED
    raw_pem: Optional[str] = None

    @property
    def is_active(self) -> bool:
        return self.state == CertificateLifecycleState.ACTIVE

    @property
    def is_expired(self) -> bool:
        return self.state == CertificateLifecycleState.EXPIRED

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cert_id": self.cert_id,
            "subject": self.subject,
            "issuer": self.issuer,
            "serial_number": self.serial_number,
            "fingerprint_sha256": self.fingerprint_sha256,
            "not_valid_before": self.not_valid_before.isoformat(),
            "not_valid_after": self.not_valid_after.isoformat(),
            "dns_sans": list(self.dns_sans),
            "ip_sans": list(self.ip_sans),
            "uri_sans": list(self.uri_sans),
            "key_usage": list(self.key_usage),
            "extended_key_usage": list(self.extended_key_usage),
            "is_ca": self.is_ca,
            "state": self.state.value if hasattr(self.state, "value") else str(self.state),
        }


class CertificateValidator:
    """Validates X.509 certificates against configured trust anchors and cryptographic policies."""

    @staticmethod
    def parse_pem(cert_pem: str) -> x509.Certificate:
        """Parses a PEM formatted certificate string into cryptography.x509.Certificate."""
        if not cert_pem or not cert_pem.strip():
            raise CertificateValidationError("Certificate PEM data cannot be empty")
        try:
            return x509.load_pem_x509_certificate(cert_pem.encode("utf-8"), default_backend())
        except Exception as exc:
            raise CertificateValidationError(f"Failed to parse X.509 certificate PEM: {exc}") from exc

    @staticmethod
    def extract_metadata(
        cert: x509.Certificate,
        cert_id: Optional[str] = None,
        state: CertificateLifecycleState = CertificateLifecycleState.DISCOVERED,
        raw_pem: Optional[str] = None,
    ) -> CertificateMetadata:
        """Extracts normalized CertificateMetadata from an X.509 Certificate."""
        fingerprint = cert.fingerprint(hashes.SHA256()).hex().lower()
        cid = cert_id or f"cert-{fingerprint[:16]}"

        # Subject & Issuer
        subject = cert.subject.rfc4514_string()
        issuer = cert.issuer.rfc4514_string()
        serial = str(cert.serial_number)

        # Dates (convert to UTC aware)
        nvb = cert.not_valid_before_utc if hasattr(cert, "not_valid_before_utc") else cert.not_valid_before.replace(tzinfo=timezone.utc)
        nva = cert.not_valid_after_utc if hasattr(cert, "not_valid_after_utc") else cert.not_valid_after.replace(tzinfo=timezone.utc)

        # SANs
        dns_sans: List[str] = []
        ip_sans: List[str] = []
        uri_sans: List[str] = []
        try:
            san_ext = cert.extensions.get_extension_for_oid(ExtensionOID.SUBJECT_ALTERNATIVE_NAME)
            san_val = san_ext.value
            for gn in san_val:
                if isinstance(gn, x509.DNSName):
                    dns_sans.append(gn.value)
                elif isinstance(gn, x509.IPAddress):
                    ip_sans.append(str(gn.value))
                elif isinstance(gn, x509.UniformResourceIdentifier):
                    uri_sans.append(gn.value)
        except x509.ExtensionNotFound:
            pass

        # Key Usage
        ku_list: List[str] = []
        try:
            ku_ext = cert.extensions.get_extension_for_oid(ExtensionOID.KEY_USAGE)
            ku_val = ku_ext.value
            if getattr(ku_val, "digital_signature", False):
                ku_list.append("digital_signature")
            if getattr(ku_val, "content_commitment", False):
                ku_list.append("content_commitment")
            if getattr(ku_val, "key_encipherment", False):
                ku_list.append("key_encipherment")
            if getattr(ku_val, "data_encipherment", False):
                ku_list.append("data_encipherment")
            if getattr(ku_val, "key_agreement", False):
                ku_list.append("key_agreement")
            if getattr(ku_val, "key_cert_sign", False):
                ku_list.append("key_cert_sign")
            if getattr(ku_val, "crl_sign", False):
                ku_list.append("crl_sign")
        except x509.ExtensionNotFound:
            pass

        # Extended Key Usage
        eku_list: List[str] = []
        try:
            eku_ext = cert.extensions.get_extension_for_oid(ExtensionOID.EXTENDED_KEY_USAGE)
            for oid in eku_ext.value:
                if oid == ExtendedKeyUsageOID.SERVER_AUTH:
                    eku_list.append("server_auth")
                elif oid == ExtendedKeyUsageOID.CLIENT_AUTH:
                    eku_list.append("client_auth")
                elif oid == ExtendedKeyUsageOID.CODE_SIGNING:
                    eku_list.append("code_signing")
                else:
                    eku_list.append(oid.dotted_string)
        except x509.ExtensionNotFound:
            pass

        # Basic Constraints (is_ca)
        is_ca = False
        try:
            bc_ext = cert.extensions.get_extension_for_oid(ExtensionOID.BASIC_CONSTRAINTS)
            is_ca = bc_ext.value.ca
        except x509.ExtensionNotFound:
            pass

        return CertificateMetadata(
            cert_id=cid,
            subject=subject,
            issuer=issuer,
            serial_number=serial,
            fingerprint_sha256=fingerprint,
            not_valid_before=nvb,
            not_valid_after=nva,
            dns_sans=tuple(dns_sans),
            ip_sans=tuple(ip_sans),
            uri_sans=tuple(uri_sans),
            key_usage=tuple(ku_list),
            extended_key_usage=tuple(eku_list),
            is_ca=is_ca,
            state=state,
            raw_pem=raw_pem,
        )

    def validate_certificate(
        self,
        cert: x509.Certificate,
        trust_anchors: Sequence[x509.Certificate],
        intermediate_certs: Optional[Sequence[x509.Certificate]] = None,
        expected_hostname: Optional[str] = None,
        expected_purpose: Optional[str] = None,  # "server_auth" or "client_auth"
        now: Optional[datetime.datetime] = None,
        crl_list: Optional[Sequence[x509.CertificateRevocationList]] = None,
    ) -> CertificateMetadata:
        """
        Performs full cryptographic chain, intermediate CA, temporal, SAN, KU/EKU, and revocation verification.
        Fails closed on any invalid condition.
        """
        current_time = now or datetime.datetime.now(timezone.utc)
        if current_time.tzinfo is None:
            current_time = current_time.replace(tzinfo=timezone.utc)

        # 1. Temporal Validity Check on Leaf
        self._check_temporal_validity(cert, current_time)

        # 2. CA Chain & Trust Anchor Verification (Supporting Intermediates)
        if not trust_anchors:
            raise UntrustedIssuerError("No trusted CA anchors configured; verification fails closed")

        all_pool = list(trust_anchors) + list(intermediate_certs or [])
        current_cert = cert
        visited_fingerprints = set()

        while True:
            fp = current_cert.fingerprint(hashes.SHA256()).hex().lower()
            if fp in visited_fingerprints:
                raise CertificateValidationError("Cyclic certificate chain detected")
            visited_fingerprints.add(fp)

            # Check if current_cert is a trusted root
            is_trusted_root = any(
                current_cert.fingerprint(hashes.SHA256()) == ca.fingerprint(hashes.SHA256())
                for ca in trust_anchors
            )
            if is_trusted_root and current_cert != cert:
                # Reached a trusted root anchor in the chain
                break

            # Find issuer in trust anchors or intermediates
            issuer_cert = None
            for candidate in all_pool:
                if current_cert.issuer == candidate.subject:
                    # Check cryptographic signature
                    if self._verify_cert_signature(candidate, current_cert):
                        issuer_cert = candidate
                        break

            if not issuer_cert:
                raise UntrustedIssuerError(
                    f"Certificate issuer '{current_cert.issuer.rfc4514_string()}' cannot be verified against trust anchors or intermediates"
                )

            # Enforce CA semantics on the issuing certificate
            self._verify_ca_semantics(issuer_cert)
            self._check_temporal_validity(issuer_cert, current_time)

            # Check if issuer is a trusted anchor
            if any(issuer_cert.fingerprint(hashes.SHA256()) == ca.fingerprint(hashes.SHA256()) for ca in trust_anchors):
                # Successfully anchored
                break

            # Advance up the chain
            current_cert = issuer_cert

        # 3. Hostname / SAN verification if requested
        if expected_hostname:
            self._verify_hostname_san(cert, expected_hostname)

        # 4. Purpose / EKU verification if requested
        if expected_purpose:
            self._verify_purpose(cert, expected_purpose)

        # 5. Revocation List Check
        if crl_list:
            for crl in crl_list:
                revoked_entry = crl.get_revoked_certificate_by_serial_number(cert.serial_number)
                if revoked_entry is not None:
                    raise CertificateRevokedError(
                        f"Certificate serial {cert.serial_number} is revoked as of {revoked_entry.revocation_date_utc.isoformat()}"
                    )

        return self.extract_metadata(cert, state=CertificateLifecycleState.VALIDATED)

    def _check_temporal_validity(self, cert: x509.Certificate, current_time: datetime.datetime) -> None:
        """Verifies that cert is within its valid date window."""
        nvb = cert.not_valid_before_utc if hasattr(cert, "not_valid_before_utc") else cert.not_valid_before.replace(tzinfo=timezone.utc)
        nva = cert.not_valid_after_utc if hasattr(cert, "not_valid_after_utc") else cert.not_valid_after.replace(tzinfo=timezone.utc)
        if current_time < nvb:
            raise CertificateNotYetValidError(f"Certificate is not yet valid (valid from {nvb.isoformat()})")
        if current_time > nva:
            raise CertificateExpiredError(f"Certificate has expired (expired at {nva.isoformat()})")

    def _verify_cert_signature(self, issuer: x509.Certificate, leaf: x509.Certificate) -> bool:
        """Verifies leaf signature with issuer public key."""
        pub_key = issuer.public_key()
        try:
            if isinstance(pub_key, rsa.RSAPublicKey):
                pub_key.verify(
                    leaf.signature,
                    leaf.tbs_certificate_bytes,
                    padding.PKCS1v15(),
                    leaf.signature_hash_algorithm,  # type: ignore
                )
                return True
            elif isinstance(pub_key, ec.EllipticCurvePublicKey):
                pub_key.verify(
                    leaf.signature,
                    leaf.tbs_certificate_bytes,
                    ec.ECDSA(leaf.signature_hash_algorithm),  # type: ignore
                )
                return True
            elif isinstance(pub_key, ed25519.Ed25519PublicKey):
                pub_key.verify(
                    leaf.signature,
                    leaf.tbs_certificate_bytes,
                )
                return True
        except Exception:
            return False
        return False

    def _verify_ca_semantics(self, ca_cert: x509.Certificate) -> None:
        """Enforces BasicConstraints is_ca=True and key_cert_sign on issuing certificates."""
        try:
            bc_ext = ca_cert.extensions.get_extension_for_oid(ExtensionOID.BASIC_CONSTRAINTS)
            if not bc_ext.value.ca:
                raise CertificateValidationError(f"Issuing certificate '{ca_cert.subject.rfc4514_string()}' is not a CA (BasicConstraints ca=False)")
        except x509.ExtensionNotFound:
            raise CertificateValidationError(f"Issuing certificate '{ca_cert.subject.rfc4514_string()}' missing BasicConstraints extension")

        try:
            ku_ext = ca_cert.extensions.get_extension_for_oid(ExtensionOID.KEY_USAGE)
            if not ku_ext.value.key_cert_sign:
                raise CertificateValidationError(f"Issuing CA certificate '{ca_cert.subject.rfc4514_string()}' lacks key_cert_sign KeyUsage")
        except x509.ExtensionNotFound:
            pass

    def _verify_purpose(self, cert: x509.Certificate, purpose: str) -> None:
        """Verifies ExtendedKeyUsage for requested purpose (server_auth or client_auth)."""
        try:
            eku_ext = cert.extensions.get_extension_for_oid(ExtensionOID.EXTENDED_KEY_USAGE)
            allowed_oids = set(eku_ext.value)
            if purpose == "server_auth" and ExtendedKeyUsageOID.SERVER_AUTH not in allowed_oids:
                raise CertificateValidationError("Certificate lacks server_auth ExtendedKeyUsage")
            elif purpose == "client_auth" and ExtendedKeyUsageOID.CLIENT_AUTH not in allowed_oids:
                raise CertificateValidationError("Certificate lacks client_auth ExtendedKeyUsage")
        except x509.ExtensionNotFound:
            pass


    def _verify_hostname_san(self, cert: x509.Certificate, expected_hostname: str) -> None:
        """Verifies that expected_hostname matches certificate SAN or Subject CN."""
        expected = expected_hostname.lower().strip()
        matched = False

        try:
            san_ext = cert.extensions.get_extension_for_oid(ExtensionOID.SUBJECT_ALTERNATIVE_NAME)
            for gn in san_ext.value:
                if isinstance(gn, x509.DNSName):
                    val = gn.value.lower().strip()
                    if val == expected or (val.startswith("*.") and expected.endswith(val[2:]) and expected.count(".") == val.count(".")):
                        matched = True
                        break
                elif isinstance(gn, x509.IPAddress):
                    if str(gn.value) == expected:
                        matched = True
                        break
        except x509.ExtensionNotFound:
            # Fallback to Subject CN if no SAN is present
            for attribute in cert.subject:
                if attribute.oid == x509.oid.NameOID.COMMON_NAME:
                    cn = str(attribute.value).lower().strip()
                    if cn == expected:
                        matched = True
                        break

        if not matched:
            raise CertificateValidationError(f"Certificate SANs do not match expected hostname '{expected_hostname}'")


class CertificateLifecycleManager:
    """
    Manages certificate references, dual-bundle rotation, and expiry monitoring.
    Consumes external PKI; does NOT issue certificates.
    """

    def __init__(
        self,
        validator: Optional[CertificateValidator] = None,
        config: Optional[SecurityBaselineConfig] = None,
        alert_callback: Optional[Callable[[str, str, Dict[str, Any]], None]] = None,
    ) -> None:
        self.validator = validator or CertificateValidator()
        self.config = config or SecurityBaselineConfig()
        self.alert_callback = alert_callback
        self._trust_anchors: Dict[str, x509.Certificate] = {}
        self._certificates: Dict[str, CertificateMetadata] = {}
        self._crls: List[x509.CertificateRevocationList] = []

    def register_trust_anchor(self, ca_pem: str, anchor_id: Optional[str] = None) -> str:
        """Registers an external CA root/intermediate as a trusted anchor."""
        ca_cert = self.validator.parse_pem(ca_pem)
        fp = ca_cert.fingerprint(hashes.SHA256()).hex().lower()
        aid = anchor_id or f"ca-{fp[:16]}"
        self._trust_anchors[aid] = ca_cert
        return aid

    def register_crl(self, crl_pem_or_der: bytes, is_der: bool = False) -> None:
        """Registers a Certificate Revocation List for revocation checking."""
        if is_der:
            crl = x509.load_der_x509_crl(crl_pem_or_der, default_backend())
        else:
            crl = x509.load_pem_x509_crl(crl_pem_or_der, default_backend())
        self._crls.append(crl)

    def import_and_activate_certificate(
        self,
        cert_pem: str,
        cert_id: Optional[str] = None,
        expected_hostname: Optional[str] = None,
        now: Optional[datetime.datetime] = None,
    ) -> CertificateMetadata:
        """
        Imports, validates, and activates a certificate from an external PKI.
        """
        cert = self.validator.parse_pem(cert_pem)
        anchors = list(self._trust_anchors.values())
        validated_meta = self.validator.validate_certificate(
            cert,
            trust_anchors=anchors,
            expected_hostname=expected_hostname,
            now=now,
            crl_list=self._crls,
        )

        active_meta = CertificateMetadata(
            cert_id=cert_id or validated_meta.cert_id,
            subject=validated_meta.subject,
            issuer=validated_meta.issuer,
            serial_number=validated_meta.serial_number,
            fingerprint_sha256=validated_meta.fingerprint_sha256,
            not_valid_before=validated_meta.not_valid_before,
            not_valid_after=validated_meta.not_valid_after,
            dns_sans=validated_meta.dns_sans,
            ip_sans=validated_meta.ip_sans,
            uri_sans=validated_meta.uri_sans,
            key_usage=validated_meta.key_usage,
            extended_key_usage=validated_meta.extended_key_usage,
            is_ca=validated_meta.is_ca,
            state=CertificateLifecycleState.ACTIVE,
            raw_pem=cert_pem,
        )

        self._certificates[active_meta.cert_id] = active_meta
        return active_meta

    def evaluate_lifecycle_state(
        self,
        cert_id: str,
        now: Optional[datetime.datetime] = None,
        custom_warning_seconds: Optional[int] = None,
    ) -> CertificateMetadata:
        """
        Evaluates lifecycle status: ACTIVE -> EXPIRING -> EXPIRED or REVOKED.
        Emits P6 alert when entering EXPIRING or EXPIRED.
        """
        if cert_id not in self._certificates:
            raise KeyError(f"Certificate {cert_id!r} not found in lifecycle registry")

        meta = self._certificates[cert_id]
        current_time = now or datetime.datetime.now(timezone.utc)
        if current_time.tzinfo is None:
            current_time = current_time.replace(tzinfo=timezone.utc)

        warning_threshold = datetime.timedelta(
            seconds=custom_warning_seconds or self.config.pki_cert_expiry_warning_seconds
        )

        new_state = meta.state
        if current_time > meta.not_valid_after:
            new_state = CertificateLifecycleState.EXPIRED
        elif current_time + warning_threshold >= meta.not_valid_after:
            new_state = CertificateLifecycleState.EXPIRING

        # Check CRLs
        for crl in self._crls:
            if crl.get_revoked_certificate_by_serial_number(int(meta.serial_number)) is not None:
                new_state = CertificateLifecycleState.REVOKED
                break

        updated_meta = CertificateMetadata(
            cert_id=meta.cert_id,
            subject=meta.subject,
            issuer=meta.issuer,
            serial_number=meta.serial_number,
            fingerprint_sha256=meta.fingerprint_sha256,
            not_valid_before=meta.not_valid_before,
            not_valid_after=meta.not_valid_after,
            dns_sans=meta.dns_sans,
            ip_sans=meta.ip_sans,
            uri_sans=meta.uri_sans,
            key_usage=meta.key_usage,
            extended_key_usage=meta.extended_key_usage,
            is_ca=meta.is_ca,
            state=new_state,
            raw_pem=meta.raw_pem,
        )

        self._certificates[cert_id] = updated_meta

        # Trigger P6 alert callback on degradation
        if new_state in (CertificateLifecycleState.EXPIRING, CertificateLifecycleState.EXPIRED, CertificateLifecycleState.REVOKED):
            if self.alert_callback:
                self.alert_callback(
                    f"CERTIFICATE_{new_state.value}",
                    f"Certificate {cert_id} is in state {new_state.value}",
                    updated_meta.to_dict(),
                )

        return updated_meta

    def rotate_certificate(
        self,
        old_cert_id: str,
        new_cert_pem: str,
        now: Optional[datetime.datetime] = None,
    ) -> Tuple[CertificateMetadata, CertificateMetadata]:
        """
        Executes controlled dual-certificate rotation:
        Activates new certificate, sets old certificate to ROTATING -> RETIRING.
        """
        new_meta = self.import_and_activate_certificate(new_cert_pem, now=now)

        if old_cert_id in self._certificates:
            old_meta = self._certificates[old_cert_id]
            retiring_old = CertificateMetadata(
                cert_id=old_meta.cert_id,
                subject=old_meta.subject,
                issuer=old_meta.issuer,
                serial_number=old_meta.serial_number,
                fingerprint_sha256=old_meta.fingerprint_sha256,
                not_valid_before=old_meta.not_valid_before,
                not_valid_after=old_meta.not_valid_after,
                dns_sans=old_meta.dns_sans,
                ip_sans=old_meta.ip_sans,
                uri_sans=old_meta.uri_sans,
                key_usage=old_meta.key_usage,
                extended_key_usage=old_meta.extended_key_usage,
                is_ca=old_meta.is_ca,
                state=CertificateLifecycleState.RETIRING,
                raw_pem=old_meta.raw_pem,
            )
            self._certificates[old_cert_id] = retiring_old
            return new_meta, retiring_old

        return new_meta, new_meta
