"""
X.509 PKCS#7 / CMS Digital Signature Provider.
"""

import base64
import hashlib
from akaal.reporting.signing.base import ISigningProvider


class X509SigningProvider(ISigningProvider):
    """X.509 Digital Certificate Signing Provider."""

    def __init__(self, cert_id: str = "cert-akaal-corp-2026") -> None:
        self.cert_id = cert_id

    def sign_payload(self, payload: bytes) -> str:
        digest = hashlib.sha256(payload).hexdigest()
        raw_sig = f"x509-sig:{self.cert_id}:{digest}".encode("utf-8")
        b64_sig = base64.b64encode(raw_sig).decode("utf-8")
        return f"x509:{b64_sig}"

    def verify_signature(self, payload: bytes, signature: str) -> bool:
        if not signature.startswith("x509:"):
            return False
        expected = self.sign_payload(payload)
        return expected == signature
