"""
Unit tests for Digital Signing Providers (NoSigning, HashSigning, X509Signing).
"""

import pytest
from akaal.reporting.signing.hash import HashSigningProvider
from akaal.reporting.signing.nosigning import NoSigningProvider
from akaal.reporting.signing.x509 import X509SigningProvider


def test_no_signing_provider():
    p = NoSigningProvider()
    payload = b"test payload content"
    sig = p.sign_payload(payload)
    assert sig == "UNSIGNED"
    assert p.verify_signature(payload, sig) is True


def test_hash_signing_provider():
    p = HashSigningProvider(secret_key="my_secret")
    payload = b"report payload payload"
    sig = p.sign_payload(payload)
    assert sig.startswith("hmac-sha256:")
    assert p.verify_signature(payload, sig) is True
    assert p.verify_signature(b"corrupted payload", sig) is False


def test_x509_signing_provider():
    p = X509SigningProvider(cert_id="cert-akaal-1")
    payload = b"report audit payload"
    sig = p.sign_payload(payload)
    assert sig.startswith("x509:")
    assert p.verify_signature(payload, sig) is True
    assert p.verify_signature(payload, "x509:invalid") is False
