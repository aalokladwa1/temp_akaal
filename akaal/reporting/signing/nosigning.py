"""
No-Op Signing Provider Implementation.
"""

from akaal.reporting.signing.base import ISigningProvider


class NoSigningProvider(ISigningProvider):
    """No-Op Signing Provider (Un-signed reports)."""

    def sign_payload(self, payload: bytes) -> str:
        return "UNSIGNED"

    def verify_signature(self, payload: bytes, signature: str) -> bool:
        return signature == "UNSIGNED"
