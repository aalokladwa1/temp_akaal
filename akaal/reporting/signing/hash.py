"""
Hash-Based (HMAC SHA-256) Signing Provider Implementation.
"""

import hashlib
import hmac
from akaal.reporting.signing.base import ISigningProvider


class HashSigningProvider(ISigningProvider):
    """Hash/HMAC SHA-256 Signing Provider."""

    def __init__(self, secret_key: str = "akaal_reporting_secret_key_2026") -> None:
        self.secret_key = secret_key.encode("utf-8")

    def sign_payload(self, payload: bytes) -> str:
        sig = hmac.new(self.secret_key, payload, hashlib.sha256).hexdigest()
        return f"hmac-sha256:{sig}"

    def verify_signature(self, payload: bytes, signature: str) -> bool:
        expected = self.sign_payload(payload)
        return hmac.compare_digest(expected, signature)
