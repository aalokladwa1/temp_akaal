"""akaalPipeline.security.federation.oidc
======================================
P7.4 OIDC & OAuth 2.0 Identity Token Validation Engine.

Strict Invariants:
1. DECODED TOKEN != VERIFIED TOKEN. Cryptographic signature verification is mandatory.
2. alg=none and algorithm confusion attacks are strictly rejected.
3. Issuer and audience verification are mandatory.
4. JWKS refresh must be concurrency safe.
5. IdP outage fails closed for new authentication.
"""

from __future__ import annotations

import base64
import datetime
import json
import logging
import threading
from datetime import timezone
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec, ed25519, padding, rsa

from akaalPipeline.contracts.enums import AuthenticationAssurance, FederationProviderType
from akaalPipeline.security.federation.models import FederatedIdentityResult, FederationProviderConfig

logger = logging.getLogger("akaalPipeline.security.federation.oidc")


class OIDCValidationError(ValueError):
    """Raised when an OIDC token fails cryptographic or semantic validation."""
    pass


class OIDCExpiredError(OIDCValidationError):
    """Raised when an OIDC token is expired."""
    pass


def _base64url_decode(input_str: str) -> bytes:
    """Decodes a base64url encoded string with padding correction."""
    rem = len(input_str) % 4
    if rem > 0:
        input_str += "=" * (4 - rem)
    return base64.urlsafe_b64decode(input_str.encode("utf-8"))


class OIDCValidator:
    """
    Validates OIDC ID Tokens and OAuth 2.0 JWTs.
    Implements dynamic JWKS verification and strict RFC 7519 validation.
    """

    ALLOWED_ALGORITHMS = {"RS256", "RS384", "RS512", "ES256", "ES384", "ES512", "EdDSA"}

    def __init__(self) -> None:
        self._jwks_cache: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def register_jwks(self, provider_id: str, jwks: Dict[str, Any]) -> None:
        """Registers or updates JWKS key set for a provider."""
        with self._lock:
            self._jwks_cache[provider_id] = jwks

    def validate_id_token(
        self,
        token: str,
        config: FederationProviderConfig,
        expected_audience: Optional[str] = None,
        now: Optional[datetime.datetime] = None,
    ) -> FederatedIdentityResult:
        """
        Performs full cryptographic signature, temporal, issuer, and audience validation on a JWT.
        Fails closed on any invalid condition.
        """
        if not token or not token.strip():
            raise OIDCValidationError("Token string cannot be empty")

        parts = token.strip().split(".")
        if len(parts) != 3:
            raise OIDCValidationError("Malformed JWT: Expected exactly 3 dot-separated segments")

        header_b64, payload_b64, signature_b64 = parts

        # 1. Parse Header
        try:
            header_json = _base64url_decode(header_b64).decode("utf-8")
            header = json.loads(header_json)
        except Exception as exc:
            raise OIDCValidationError(f"Invalid JWT header format: {exc}") from exc

        alg = header.get("alg")
        if not alg or alg.lower() == "none" or alg not in self.ALLOWED_ALGORITHMS:
            raise OIDCValidationError(f"Disallowed or insecure JWT algorithm: {alg!r}")

        # 2. Parse Payload
        try:
            payload_json = _base64url_decode(payload_b64).decode("utf-8")
            payload = json.loads(payload_json)
        except Exception as exc:
            raise OIDCValidationError(f"Invalid JWT payload format: {exc}") from exc

        # 3. Temporal Validity
        current_time = now or datetime.datetime.now(timezone.utc)
        current_ts = int(current_time.timestamp())

        exp = payload.get("exp")
        if exp is None or not isinstance(exp, (int, float)):
            raise OIDCValidationError("JWT missing mandatory 'exp' expiration claim")
        if current_ts >= exp:
            raise OIDCExpiredError(f"JWT has expired at {datetime.datetime.fromtimestamp(exp, tz=timezone.utc).isoformat()}")

        nbf = payload.get("nbf")
        if nbf is not None and isinstance(nbf, (int, float)):
            if current_ts < nbf:
                raise OIDCValidationError("JWT is not yet valid (nbf in future)")

        # 4. Issuer Validation
        iss = payload.get("iss")
        if not iss or iss != config.issuer:
            raise OIDCValidationError(f"JWT issuer '{iss}' does not match configured issuer '{config.issuer}'")

        # 5. Audience Validation
        aud = payload.get("aud")
        expected_aud = expected_audience or config.client_id
        if expected_aud:
            if isinstance(aud, str):
                if aud != expected_aud:
                    raise OIDCValidationError(f"JWT audience '{aud}' does not match expected '{expected_aud}'")
            elif isinstance(aud, list):
                if expected_aud not in aud:
                    raise OIDCValidationError(f"JWT audience list does not contain expected '{expected_aud}'")
            else:
                raise OIDCValidationError("JWT missing valid 'aud' audience claim")

        # 6. Cryptographic Signature Verification
        signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
        try:
            signature_bytes = _base64url_decode(signature_b64)
        except Exception as exc:
            raise OIDCValidationError(f"Invalid signature base64 encoding: {exc}") from exc

        kid = header.get("kid")
        self._verify_signature(
            alg=alg,
            signing_input=signing_input,
            signature_bytes=signature_bytes,
            kid=kid,
            config=config,
        )

        # 7. Extract normalized identity
        sub = payload.get("sub")
        if not sub:
            raise OIDCValidationError("JWT missing mandatory 'sub' subject claim")

        email = payload.get("email")
        display_name = payload.get("name") or payload.get("preferred_username")
        groups = payload.get("groups", [])
        if isinstance(groups, str):
            groups = [groups]

        # Determine assurance from ACR / AMR
        assurance = AuthenticationAssurance.MEDIUM
        amr = payload.get("amr", [])
        if isinstance(amr, list) and ("mfa" in amr or "fido" in amr or "hwk" in amr):
            assurance = AuthenticationAssurance.HIGH

        expires_dt = datetime.datetime.fromtimestamp(exp, tz=timezone.utc)

        return FederatedIdentityResult(
            provider_id=config.provider_id,
            provider_type=config.provider_type,
            subject=str(sub),
            email=str(email) if email else None,
            display_name=str(display_name) if display_name else None,
            groups=tuple(str(g) for g in groups),
            claims=payload,
            assurance=assurance,
            expires_at=expires_dt,
        )

    def _verify_signature(
        self,
        alg: str,
        signing_input: bytes,
        signature_bytes: bytes,
        kid: Optional[str],
        config: FederationProviderConfig,
    ) -> None:
        """Verifies JWT cryptographic signature against configured JWKS or provider keys."""
        jwks = self._jwks_cache.get(config.provider_id) or config.jwks_keys
        if not jwks or "keys" not in jwks:
            raise OIDCValidationError(f"No JWKS configured or available for provider '{config.provider_id}'")

        keys = jwks["keys"]
        matched_key_dict = None
        if kid:
            for k in keys:
                if k.get("kid") == kid:
                    matched_key_dict = k
                    break
        else:
            if len(keys) == 1:
                matched_key_dict = keys[0]

        if not matched_key_dict:
            raise OIDCValidationError(f"Signing key with kid={kid!r} not found in JWKS for provider '{config.provider_id}'")

        # Convert JWK to Cryptography public key
        public_key = self._jwk_to_public_key(matched_key_dict)

        try:
            if alg.startswith("RS"):
                hash_alg = hashes.SHA256() if alg == "RS256" else (hashes.SHA384() if alg == "RS384" else hashes.SHA512())
                assert isinstance(public_key, rsa.RSAPublicKey)
                public_key.verify(signature_bytes, signing_input, padding.PKCS1v15(), hash_alg)
            elif alg.startswith("ES"):
                hash_alg = hashes.SHA256() if alg == "ES256" else (hashes.SHA384() if alg == "ES384" else hashes.SHA512())
                assert isinstance(public_key, ec.EllipticCurvePublicKey)
                # Convert raw IEEE P1363 (r || s) signature to DER if necessary
                sig = signature_bytes
                if len(sig) == 64:  # ES256 P1363
                    r = int.from_bytes(sig[:32], "big")
                    s = int.from_bytes(sig[32:], "big")
                    from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature
                    sig = encode_dss_signature(r, s)
                public_key.verify(sig, signing_input, ec.ECDSA(hash_alg))
            elif alg == "EdDSA":
                assert isinstance(public_key, ed25519.Ed25519PublicKey)
                public_key.verify(signature_bytes, signing_input)
            else:
                raise OIDCValidationError(f"Unsupported algorithm: {alg}")
        except Exception as exc:
            raise OIDCValidationError(f"JWT signature verification failed: {exc}") from exc

    def _jwk_to_public_key(self, jwk: Dict[str, Any]) -> Any:
        """Converts an RFC 7517 JWK dict into a Cryptography public key."""
        kty = jwk.get("kty")
        if kty == "RSA":
            n_bytes = _base64url_decode(jwk["n"])
            e_bytes = _base64url_decode(jwk["e"])
            n = int.from_bytes(n_bytes, "big")
            e = int.from_bytes(e_bytes, "big")
            return rsa.RSAPublicNumbers(e, n).public_key(default_backend())
        elif kty == "EC":
            crv = jwk.get("crv")
            x_bytes = _base64url_decode(jwk["x"])
            y_bytes = _base64url_decode(jwk["y"])
            x = int.from_bytes(x_bytes, "big")
            y = int.from_bytes(y_bytes, "big")
            curve: ec.EllipticCurve = ec.SECP256R1() if crv == "P-256" else (ec.SECP384R1() if crv == "P-384" else ec.SECP521R1())
            return ec.EllipticCurvePublicNumbers(x, y, curve).public_key(default_backend())
        elif kty == "OKP" and jwk.get("crv") == "Ed25519":
            x_bytes = _base64url_decode(jwk["x"])
            return ed25519.Ed25519PublicKey.from_public_bytes(x_bytes)
        else:
            raise OIDCValidationError(f"Unsupported JWK key type: kty={kty!r}")
