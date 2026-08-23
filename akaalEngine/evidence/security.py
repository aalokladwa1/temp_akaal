"""
akaalEngine.evidence.security
=============================
EvidenceSecuritySanitizer for Authority #12.
Reuses canonical Authority #7 TelemetrySanitizer / Authority #5 secret rules to perform recursive secret redaction
across evidence facts, metadata, URIs, and payloads before evidence digest computation or persistence.
"""

import re
from typing import Any, Dict, List, Mapping, Union

from akaalEngine.telemetry.security.sanitizer import TelemetrySanitizer

_URL_CRED_REGEX = re.compile(r"://([^:@]+):([^@]+)@")


class EvidenceSecuritySanitizer:
    """
    Recursively scrubs secrets, credentials, tokens, bearer headers, AWS keys,
    private keys, and connection URI credentials from evidence payloads.
    """

    @classmethod
    def sanitize(cls, data: Any) -> Any:
        """Recursively scrubs secret material from text, dicts, lists, and metadata structures."""
        if data is None:
            return None
        if isinstance(data, str):
            return cls.sanitize_string(data)
        if isinstance(data, Mapping):
            return cls.sanitize_mapping(data)
        if isinstance(data, (list, tuple)):
            return [cls.sanitize(item) for item in data]
        return data

    @classmethod
    def sanitize_string(cls, text: str) -> str:
        if not text:
            return text
        # Redact connection string credentials (e.g., scheme://user:pass@host)
        text = _URL_CRED_REGEX.sub("://[REDACTED]:[REDACTED]@", text)

        # Delegate to canonical TelemetrySanitizer for keyword scrubbing
        sanitized = TelemetrySanitizer.sanitize_string(text)
        return sanitized

    @classmethod
    def sanitize_mapping(cls, mapping: Mapping[str, Any]) -> Dict[str, Any]:
        result = {}
        for key, val in mapping.items():
            k_lower = key.lower()
            if any(kw in k_lower for kw in ("pass", "password", "passwd", "secret", "bearer", "private_key", "api_key", "access_token", "auth_token", "token", "connection_string", "credentials", "client_secret", "authorization")) and not any(safe in k_lower for safe in ("fencing", "attempt", "resource", "bypassed", "compass")):
                if isinstance(val, (Mapping, list, tuple)):
                    # Recurse inside container mapping/list
                    result[key] = cls.sanitize(val)
                else:
                    result[key] = "[REDACTED]"
            else:
                result[key] = cls.sanitize(val)
        return result
