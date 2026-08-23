"""
akaalEngine.telemetry.security.sanitizer
=========================================
TelemetrySanitizer for secret scrubbing across operational events, metric labels,
and structured logs. Reuses Authority #5 secret sanitization rules.
"""

from typing import Any, Dict, List, Mapping, Union

_SECRET_KEYWORDS = (
    "password", "secret", "bearer", "private_key", "api_key",
    "access_token", "auth_token", "connection_string", "credentials",
)


class TelemetrySanitizer:
    """
    Scubs secret material from text, dictionaries, lists, and metadata structures
    before emitting telemetry or logs.
    """

    @classmethod
    def sanitize(cls, data: Any) -> Any:
        if isinstance(data, str):
            return cls.sanitize_string(data)
        elif isinstance(data, Mapping):
            return cls.sanitize_mapping(data)
        elif isinstance(data, (list, tuple)):
            return [cls.sanitize(item) for item in data]
        return data

    @classmethod
    def sanitize_string(cls, text: str) -> str:
        # Avoid redacting positional token names like fencing_token or attempt_token
        lowered = text.lower()
        if any(keyword in lowered for keyword in _SECRET_KEYWORDS) and not any(safe in lowered for safe in ("fencing", "attempt", "resource")):
            # If string looks like key=val or contains secret substring
            if ":" in text or "=" in text or "bearer " in lowered or "-----begin" in lowered:
                return "[REDACTED]"
        return text

    @classmethod
    def sanitize_mapping(cls, mapping: Mapping[str, Any]) -> Dict[str, Any]:
        result = {}
        for key, val in mapping.items():
            k_lower = key.lower()
            if any(keyword in k_lower for keyword in _SECRET_KEYWORDS) and not any(safe in k_lower for safe in ("fencing", "attempt", "resource")):
                result[key] = "[REDACTED]"
            else:
                result[key] = cls.sanitize(val)
        return result
