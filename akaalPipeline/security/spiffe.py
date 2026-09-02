"""akaalPipeline.security.spiffe
==============================
P7.3 Workload Identity & SPIFFE/SPIRE Integration Client.

Strict Invariants:
1. AKAAL IS A SPIFFE/SPIRE CONSUMER — NOT A SPIRE SERVER.
2. A string starting with 'spiffe://' is a CLAIM, NOT a verified identity.
3. SVID verification requires cryptographic proof against configured SPIFFE trust bundles.
4. SPIRE outage NEVER extends SVID validity — expired identity fails closed.
5. In-process/network locality cannot substitute for verified SPIFFE identity.
"""

from __future__ import annotations

import datetime
import logging
import re
import urllib.parse
from dataclasses import dataclass, field
from datetime import timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple

from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import ec, ed25519, padding, rsa
from cryptography.x509.oid import ExtensionOID


from akaalPipeline.contracts.enums import (
    AuthenticationAssurance,
    AuthenticationState,
    CredentialMechanism,
    PrincipalType,
)
from akaalPipeline.security.context import PipelineActorContext

logger = logging.getLogger("akaalPipeline.security.spiffe")

# RFC 3986 and SPIFFE Standard URI Regex
SPIFFE_URI_PATTERN = re.compile(
    r"^spiffe://(?P<trust_domain>[a-z0-9\.\-_]+)(?P<path>/[a-zA-Z0-9\.\-_/]*)$"
)


class SpiffeValidationError(ValueError):
    """Raised when a SPIFFE ID or SVID fails cryptographic/structural validation."""
    pass


class SpiffeExpiredError(SpiffeValidationError):
    """Raised when a SPIFFE SVID has expired."""
    pass


class SpiffeTrustDomainMismatchError(SpiffeValidationError):
    """Raised when SVID trust domain does not match expected trust domain."""
    pass


@dataclass(frozen=True)
class SpiffeID:
    """Parsed and structurally validated SPIFFE Identity URI."""

    uri: str
    trust_domain: str
    path: str

    @classmethod
    def parse(cls, spiffe_uri: str) -> SpiffeID:
        """Parses and strictly validates a SPIFFE URI string."""
        if not spiffe_uri or not isinstance(spiffe_uri, str):
            raise SpiffeValidationError("SPIFFE URI cannot be empty")

        match = SPIFFE_URI_PATTERN.match(spiffe_uri.strip())
        if not match:
            raise SpiffeValidationError(f"Invalid SPIFFE URI format: {spiffe_uri!r}")

        td = match.group("trust_domain")
        path = match.group("path")

        if not td:
            raise SpiffeValidationError("SPIFFE URI must have a valid non-empty trust domain")
        if not path or path == "/":
            raise SpiffeValidationError("SPIFFE URI must have a non-empty workload path")

        return cls(uri=spiffe_uri.strip(), trust_domain=td, path=path)

    def __str__(self) -> str:
        return self.uri


@dataclass(frozen=True)
class SpiffeX509SVID:
    """Represents a verified SPIFFE X.509 SVID."""

    spiffe_id: SpiffeID
    certificate: x509.Certificate
    expires_at: datetime.datetime
    raw_cert_pem: str

    @property
    def is_expired(self) -> bool:
        now = datetime.datetime.now(timezone.utc)
        return now >= self.expires_at


@dataclass(frozen=True)
class SpiffeJWTSVID:
    """Represents a verified SPIFFE JWT SVID."""

    spiffe_id: SpiffeID
    audience: Tuple[str, ...]
    expires_at: datetime.datetime
    raw_token: str
    claims: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_expired(self) -> bool:
        now = datetime.datetime.now(timezone.utc)
        return now >= self.expires_at


class SpiffeSVIDValidator:
    """
    Validates X.509 and JWT SVIDs against authoritative SPIFFE trust bundles.
    Fails closed on signature failure, expiration, or trust domain mismatch.
    """

    def __init__(
        self,
        trust_bundles: Optional[Dict[str, List[x509.Certificate]]] = None,
        jwt_bundles: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> None:
        # trust_bundles: map of trust_domain -> list of CA certificates
        self.trust_bundles: Dict[str, List[x509.Certificate]] = trust_bundles or {}
        # jwt_bundles: map of trust_domain -> JWKS keys dict
        self.jwt_bundles: Dict[str, Dict[str, Any]] = jwt_bundles or {}

    def register_trust_bundle(self, trust_domain: str, ca_certificates: Sequence[x509.Certificate]) -> None:
        """Registers CA trust bundle for a specific SPIFFE trust domain."""
        if trust_domain not in self.trust_bundles:
            self.trust_bundles[trust_domain] = []
        self.trust_bundles[trust_domain].extend(ca_certificates)

    def register_jwt_bundle(self, trust_domain: str, jwks: Dict[str, Any]) -> None:
        """Registers JWT JWKS bundle for a specific SPIFFE trust domain."""
        self.jwt_bundles[trust_domain] = jwks

    def validate_jwt_svid(
        self,
        token: str,
        expected_audience: str,
        expected_trust_domain: Optional[str] = None,
        now: Optional[datetime.datetime] = None,
    ) -> SpiffeJWTSVID:
        """
        Validates SPIFFE JWT-SVID:
        1. Checks header algorithm (whitelisted, rejects none).
        2. Validates sub as a valid SPIFFE ID.
        3. Validates trust domain and audience.
        4. Validates temporal validity.
        5. Validates cryptographic signature against SPIFFE JWT bundle.
        """
        import base64
        import json
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import ec, padding, rsa

        if not token or not token.strip():
            raise SpiffeValidationError("JWT-SVID token string cannot be empty")

        parts = token.strip().split(".")
        if len(parts) != 3:
            raise SpiffeValidationError("Malformed JWT-SVID: Expected exactly 3 segments")

        header_b64, payload_b64, sig_b64 = parts

        def _b64decode(s: str) -> bytes:
            rem = len(s) % 4
            if rem > 0:
                s += "=" * (4 - rem)
            return base64.urlsafe_b64decode(s.encode("utf-8"))

        try:
            header = json.loads(_b64decode(header_b64).decode("utf-8"))
            payload = json.loads(_b64decode(payload_b64).decode("utf-8"))
        except Exception as exc:
            raise SpiffeValidationError(f"Invalid JWT-SVID format: {exc}") from exc

        alg = header.get("alg")
        if not alg or alg.lower() == "none" or alg not in ("RS256", "RS384", "RS512", "ES256", "ES384", "ES512"):
            raise SpiffeValidationError(f"Disallowed or insecure JWT-SVID algorithm: {alg!r}")

        # Subject & SPIFFE ID
        sub = payload.get("sub")
        if not sub:
            raise SpiffeValidationError("JWT-SVID missing mandatory 'sub' claim")

        spiffe_id = SpiffeID.parse(str(sub))

        # Trust Domain
        if expected_trust_domain and spiffe_id.trust_domain != expected_trust_domain:
            raise SpiffeTrustDomainMismatchError(
                f"JWT-SVID trust domain '{spiffe_id.trust_domain}' does not match expected '{expected_trust_domain}'"
            )

        # Audience
        aud = payload.get("aud")
        aud_list = [aud] if isinstance(aud, str) else (aud if isinstance(aud, list) else [])
        if expected_audience not in aud_list:
            raise SpiffeValidationError(f"JWT-SVID audience does not contain expected '{expected_audience}'")

        # Temporal Validity
        current_time = now or datetime.datetime.now(timezone.utc)
        current_ts = int(current_time.timestamp())

        exp = payload.get("exp")
        if exp is None or current_ts >= exp:
            raise SpiffeExpiredError("JWT-SVID has expired")

        nbf = payload.get("nbf")
        if nbf is not None and current_ts < nbf:
            raise SpiffeValidationError("JWT-SVID is not yet valid")

        # Signature Check
        bundle = self.jwt_bundles.get(spiffe_id.trust_domain)
        if not bundle or "keys" not in bundle:
            raise SpiffeValidationError(f"No JWT trust bundle configured for SPIFFE trust domain '{spiffe_id.trust_domain}'")

        kid = header.get("kid")
        matched_key = None
        for k in bundle["keys"]:
            if not kid or k.get("kid") == kid:
                matched_key = k
                break

        if not matched_key:
            raise SpiffeValidationError(f"No matching public key found in JWT bundle for trust domain '{spiffe_id.trust_domain}'")

        # Convert JWK to Public Key
        kty = matched_key.get("kty")
        signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
        sig_bytes = _b64decode(sig_b64)

        try:
            if kty == "RSA":
                n = int.from_bytes(_b64decode(matched_key["n"]), "big")
                e = int.from_bytes(_b64decode(matched_key["e"]), "big")
                pub_key = rsa.RSAPublicNumbers(e, n).public_key(default_backend())
                hash_alg = hashes.SHA256() if alg == "RS256" else (hashes.SHA384() if alg == "RS384" else hashes.SHA512())
                pub_key.verify(sig_bytes, signing_input, padding.PKCS1v15(), hash_alg)
            elif kty == "EC":
                x = int.from_bytes(_b64decode(matched_key["x"]), "big")
                y = int.from_bytes(_b64decode(matched_key["y"]), "big")
                curve = ec.SECP256R1() if matched_key.get("crv") == "P-256" else ec.SECP384R1()
                pub_key = ec.EllipticCurvePublicNumbers(x, y, curve).public_key(default_backend())
                sig = sig_bytes
                if len(sig) == 64:
                    from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature
                    sig = encode_dss_signature(int.from_bytes(sig[:32], "big"), int.from_bytes(sig[32:], "big"))
                hash_alg = hashes.SHA256() if alg == "ES256" else (hashes.SHA384() if alg == "ES384" else hashes.SHA512())
                pub_key.verify(sig, signing_input, ec.ECDSA(hash_alg))
            else:
                raise SpiffeValidationError(f"Unsupported key type: {kty}")
        except Exception as exc:
            raise SpiffeValidationError(f"JWT-SVID signature verification failed: {exc}") from exc

        return SpiffeJWTSVID(
            spiffe_id=spiffe_id,
            audience=tuple(aud_list),
            expires_at=datetime.datetime.fromtimestamp(exp, tz=timezone.utc),
            raw_token=token,
            claims=payload,
        )


    def validate_x509_svid(
        self,
        cert_pem: str,
        expected_trust_domain: Optional[str] = None,
        expected_workload_path: Optional[str] = None,
        now: Optional[datetime.datetime] = None,
    ) -> SpiffeX509SVID:
        """
        Validates X.509 SVID leaf certificate against configured SPIFFE trust bundle:
        1. Checks SAN for valid SPIFFE URI.
        2. Validates trust domain.
        3. Validates temporal validity.
        4. Validates cryptographic signature against trust bundle.
        """
        current_time = now or datetime.datetime.now(timezone.utc)
        if current_time.tzinfo is None:
            current_time = current_time.replace(tzinfo=timezone.utc)

        try:
            cert = x509.load_pem_x509_certificate(cert_pem.encode("utf-8"), default_backend())
        except Exception as exc:
            raise SpiffeValidationError(f"Invalid X.509 SVID PEM: {exc}") from exc

        # 1. Extract SPIFFE URI from SAN
        spiffe_uris: List[str] = []
        try:
            san_ext = cert.extensions.get_extension_for_oid(ExtensionOID.SUBJECT_ALTERNATIVE_NAME)
            for gn in san_ext.value:
                if isinstance(gn, x509.UniformResourceIdentifier) and gn.value.startswith("spiffe://"):
                    spiffe_uris.append(gn.value)
        except x509.ExtensionNotFound:
            pass

        if not spiffe_uris:
            raise SpiffeValidationError("Certificate SAN does not contain a SPIFFE URI (spiffe://)")
        if len(spiffe_uris) > 1:
            raise SpiffeValidationError("Certificate contains multiple SPIFFE URIs; ambiguous workload identity")

        spiffe_id = SpiffeID.parse(spiffe_uris[0])

        # 2. Validate Trust Domain Match
        if expected_trust_domain and spiffe_id.trust_domain != expected_trust_domain:
            raise SpiffeTrustDomainMismatchError(
                f"SVID trust domain '{spiffe_id.trust_domain}' does not match expected '{expected_trust_domain}'"
            )

        # 3. Validate Workload Path Match if specified
        if expected_workload_path and spiffe_id.path != expected_workload_path:
            raise SpiffeValidationError(
                f"SVID workload path '{spiffe_id.path}' does not match expected '{expected_workload_path}'"
            )

        # 4. Temporal Validity
        nvb = cert.not_valid_before_utc if hasattr(cert, "not_valid_before_utc") else cert.not_valid_before.replace(tzinfo=timezone.utc)
        nva = cert.not_valid_after_utc if hasattr(cert, "not_valid_after_utc") else cert.not_valid_after.replace(tzinfo=timezone.utc)

        if current_time < nvb:
            raise SpiffeValidationError(f"X.509 SVID is not yet valid (valid from {nvb.isoformat()})")
        if current_time > nva:
            raise SpiffeExpiredError(f"X.509 SVID has expired (expired at {nva.isoformat()})")

        # 5. Cryptographic signature check against trust bundle
        bundle = self.trust_bundles.get(spiffe_id.trust_domain, [])
        if not bundle:
            raise SpiffeValidationError(f"No trust bundle configured for SPIFFE trust domain '{spiffe_id.trust_domain}'")

        verified = False
        for ca in bundle:
            if cert.issuer == ca.subject:
                pub_key = ca.public_key()
                try:
                    if isinstance(pub_key, rsa.RSAPublicKey):
                        pub_key.verify(
                            cert.signature,
                            cert.tbs_certificate_bytes,
                            padding.PKCS1v15(),
                            cert.signature_hash_algorithm,  # type: ignore
                        )
                        verified = True
                        break
                    elif isinstance(pub_key, ec.EllipticCurvePublicKey):
                        pub_key.verify(
                            cert.signature,
                            cert.tbs_certificate_bytes,
                            ec.ECDSA(cert.signature_hash_algorithm),  # type: ignore
                        )
                        verified = True
                        break
                    elif isinstance(pub_key, ed25519.Ed25519PublicKey):
                        pub_key.verify(
                            cert.signature,
                            cert.tbs_certificate_bytes,
                        )
                        verified = True
                        break
                except Exception:
                    pass

        if not verified:
            raise SpiffeValidationError(f"X.509 SVID signature cannot be verified against trust bundle for '{spiffe_id.trust_domain}'")


        return SpiffeX509SVID(
            spiffe_id=spiffe_id,
            certificate=cert,
            expires_at=nva,
            raw_cert_pem=cert_pem,
        )

    def mint_pipeline_workload_context(
        self,
        svid: SpiffeX509SVID,
        organization_id: str,
        target_workload: Optional[str] = None,
    ) -> PipelineActorContext:
        """
        Creates an authoritative PipelineActorContext for an authenticated SPIFFE Workload.
        """
        return PipelineActorContext(
            actor_id=svid.spiffe_id.uri,
            actor_type=PrincipalType.WORKLOAD.value,
            display_name=f"Workload {svid.spiffe_id.path}",
            organization_id=organization_id,
            credential_mechanism=CredentialMechanism.SPIFFE_X509_SVID,
            authentication_state=AuthenticationState.AUTHENTICATED,
            authentication_assurance=AuthenticationAssurance.HIGH,
            trust_domain=svid.spiffe_id.trust_domain,
            workload_identity=svid.spiffe_id.uri,
            calling_workload=svid.spiffe_id.uri,
            target_workload=target_workload,
            expires_at=svid.expires_at.isoformat(),
        )


class SpireWorkloadClient:
    """
    Client for consuming workload credentials from SPIRE Workload API or local SVID sources.
    Enforces that SPIRE outage NEVER extends cached SVID lifetime.
    """

    def __init__(
        self,
        validator: SpiffeSVIDValidator,
        workload_socket_path: Optional[str] = None,
        cached_svid: Optional[SpiffeX509SVID] = None,
    ) -> None:
        self.validator = validator
        self.workload_socket_path = workload_socket_path
        self._cached_svid: Optional[SpiffeX509SVID] = cached_svid

    def set_cached_svid(self, svid: SpiffeX509SVID) -> None:
        """Updates currently active in-memory cached SVID."""
        self._cached_svid = svid

    def get_active_svid(self, now: Optional[datetime.datetime] = None) -> SpiffeX509SVID:
        """
        Retrieves the active SVID.
        Fails closed with SpiffeExpiredError if SVID has expired during a SPIRE outage.
        """
        current_time = now or datetime.datetime.now(timezone.utc)
        if current_time.tzinfo is None:
            current_time = current_time.replace(tzinfo=timezone.utc)

        if not self._cached_svid:
            raise SpiffeValidationError("No active SPIFFE SVID available (SPIRE offline / uninitialized)")

        if current_time >= self._cached_svid.expires_at:
            raise SpiffeExpiredError(
                f"Cached SVID {self._cached_svid.spiffe_id.uri} has expired at {self._cached_svid.expires_at.isoformat()}; "
                "cannot extend lifetime during SPIRE outage"
            )

        return self._cached_svid
