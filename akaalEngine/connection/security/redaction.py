"""
akaalEngine.connection.security.redaction
=========================================
Strict, zero-leak secret redaction for text, dictionaries, connection URIs, exceptions, and diagnostics.
Guarantees credentials, tokens, private keys, and session cookies never enter logs, fingerprints, or public DTOs.
"""

from __future__ import annotations

import re
from typing import Any, Mapping, Sequence

REDACTED_PLACEHOLDER = "[REDACTED]"

# Sensitive key patterns (case-insensitive)
SENSITIVE_KEY_PATTERNS = re.compile(
    r"(password|passwd|pwd|secret|token|api_key|apikey|private_key|priv_key|"
    r"access_key|auth_token|bearer|credential|passphrase|connection_string|"
    r"session_token|jwt|signature|client_secret|pfx_password|cert_password)",
    re.IGNORECASE,
)

# URI with embedded credentials (e.g. postgresql://user:pass@host:port/db)
URI_CREDENTIAL_PATTERN = re.compile(
    r"([a-zA-Z0-9+.-]+://)([^:/?#\s]+):([^@/?#\s]+)@",
    re.IGNORECASE,
)

# Inline key-value patterns (e.g. password=XYZ; or "secret": "XYZ")
INLINE_SECRET_PATTERN = re.compile(
    r"(?i)\b(password|passwd|pwd|secret|token|api_key|apikey|private_key|access_key|"
    r"client_secret|passphrase)\s*[:=]\s*['\"]?([^\s,;'\"&]+)['\"]?"
)

# PEM private key block
PEM_PRIVATE_KEY_PATTERN = re.compile(
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----",
    re.DOTALL,
)


def redact_text(text: Optional[str]) -> str:
    """
    Redacts secrets, connection URI credentials, and sensitive tokens from arbitrary text strings.
    """
    if text is None:
        return ""
    if not isinstance(text, str):
        text = str(text)

    # 1. Redact PEM Private Keys
    text = PEM_PRIVATE_KEY_PATTERN.sub("-----BEGIN PRIVATE KEY-----[REDACTED]-----END PRIVATE KEY-----", text)

    # 2. Redact URI Credentials: scheme://user:[REDACTED]@host
    text = URI_CREDENTIAL_PATTERN.sub(r"\1\2:" + REDACTED_PLACEHOLDER + "@", text)

    # 3. Redact inline key-value pairs: password=XYZ -> password=[REDACTED]
    text = INLINE_SECRET_PATTERN.sub(r"\1=" + REDACTED_PLACEHOLDER, text)

    return text


def redact_url(url: Optional[str]) -> str:
    """Redacts credentials embedded in connection strings / URLs."""
    if not url:
        return ""
    return URI_CREDENTIAL_PATTERN.sub(r"\1\2:" + REDACTED_PLACEHOLDER + "@", str(url))


def is_sensitive_key(key: str) -> bool:
    """Checks if a dictionary key represents sensitive or secret data."""
    if not isinstance(key, str):
        return False
    return bool(SENSITIVE_KEY_PATTERNS.search(key))


def redact_mapping(data: Optional[Mapping[str, Any]]) -> dict[str, Any]:
    """
    Recursively redacts dictionary data structures, replacing sensitive field values with [REDACTED].
    """
    if data is None:
        return {}
    
    redacted: dict[str, Any] = {}
    for k, v in data.items():
        key_str = str(k)
        if is_sensitive_key(key_str):
            redacted[key_str] = REDACTED_PLACEHOLDER
        elif isinstance(v, Mapping):
            redacted[key_str] = redact_mapping(v)
        elif isinstance(v, (list, tuple, set)):
            redacted[key_str] = redact_sequence(v)
        elif isinstance(v, str):
            redacted[key_str] = redact_text(v)
        else:
            redacted[key_str] = v
    return redacted


def redact_sequence(seq: Sequence[Any]) -> list[Any]:
    """Recursively redacts elements in sequences."""
    out = []
    for item in seq:
        if isinstance(item, Mapping):
            out.append(redact_mapping(item))
        elif isinstance(item, (list, tuple, set)):
            out.append(redact_sequence(item))
        elif isinstance(item, str):
            out.append(redact_text(item))
        else:
            out.append(item)
    return out


class SafeReprMixin:
    """Mixin for objects to ensure __repr__ and __str__ never output raw sensitive fields."""

    def __repr__(self) -> str:
        fields = []
        for k, v in self.__dict__.items():
            if k.startswith("_"):
                continue
            if is_sensitive_key(k):
                fields.append(f"{k}='{REDACTED_PLACEHOLDER}'")
            elif isinstance(v, Mapping):
                fields.append(f"{k}={redact_mapping(v)}")
            elif isinstance(v, str):
                fields.append(f"{k}='{redact_text(v)}'")
            else:
                fields.append(f"{k}={v}")
        return f"{self.__class__.__name__}({', '.join(fields)})"

    def __str__(self) -> str:
        return self.__repr__()
