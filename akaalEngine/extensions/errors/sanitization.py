"""
akaalEngine.extensions.errors.sanitization
=========================================
Error message sanitization to prevent accidental exposure of raw secrets, internal filesystem paths, and private stack traces.
"""

from __future__ import annotations

import re


_SENSITIVE_PATTERNS = [
    (re.compile(r"(password|pwd|secret|token|apikey|auth_token|client_secret)\s*[:=]\s*([^\s,;]+)", re.IGNORECASE), r"\1=***REDACTED***"),
    (re.compile(r"(Bearer\s+)[A-Za-z0-9\-\._~\+\/]+=*", re.IGNORECASE), r"\1***REDACTED***"),
    (re.compile(r"(Basic\s+)[A-Za-z0-9\+\/]+=*", re.IGNORECASE), r"\1***REDACTED***"),
]


def sanitize_error_message(msg: str) -> str:
    """Strips secret values from error messages."""
    if not msg or not isinstance(msg, str):
        return ""
    sanitized = msg
    for pattern, repl in _SENSITIVE_PATTERNS:
        sanitized = pattern.sub(repl, sanitized)
    return sanitized
