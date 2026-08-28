"""akaal.core.crypto_random
========================
Canonical OS CSPRNG Authority.
Strictly relies on secrets / os.urandom. Zero fallback to insecure pseudo-random generators.
"""

from __future__ import annotations

import os
import secrets
import uuid


class CSPRNGUnavailableError(RuntimeError):
    """Raised when the OS cryptographic random number generator fails or is unavailable."""
    pass


CryptographicEntropyError = CSPRNGUnavailableError


class CryptoRandomAuthority:
    """Canonical OS CSPRNG wrapper authority."""
    @staticmethod
    def random_bytes(n_bytes: int) -> bytes:
        return secure_random_bytes(n_bytes)

    @staticmethod
    def generate_nonce() -> str:
        return generate_nonce()


def secure_random_bytes(n_bytes: int) -> bytes:
    """Generate n_bytes using OS CSPRNG. Fail-closed on error."""
    if n_bytes <= 0:
        raise ValueError("n_bytes must be positive")
    try:
        data = secrets.token_bytes(n_bytes)
        if len(data) != n_bytes:
            raise CSPRNGUnavailableError("OS CSPRNG returned insufficient entropy")
        return data
    except Exception as exc:
        raise CSPRNGUnavailableError(f"OS CSPRNG failure: {exc}") from exc


generate_secure_random_bytes = secure_random_bytes


def generate_nonce() -> str:
    """Generate a high-entropy 128-bit UUID4 nonce using OS CSPRNG."""
    try:
        return str(uuid.UUID(bytes=secure_random_bytes(16), version=4))
    except Exception as exc:
        raise CSPRNGUnavailableError(f"Nonce generation failed: {exc}") from exc


def generate_salt(n_bytes: int = 16) -> bytes:
    """Generate a cryptographic salt of n_bytes."""
    return secure_random_bytes(n_bytes)


def generate_salt_hex(n_bytes: int = 16) -> str:
    """Generate a cryptographic salt as a hex string."""
    return generate_salt(n_bytes).hex()


def generate_secure_token(n_bytes: int = 32) -> str:
    """Generate a cryptographically secure hex token."""
    return secure_random_bytes(n_bytes).hex()


def generate_secure_id(prefix: str = "id", n_bytes: int = 16) -> str:
    """Generate a secure prefixed ID."""
    return f"{prefix}-{secure_random_bytes(n_bytes).hex()}"
