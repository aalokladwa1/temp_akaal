"""
AKAAL Log & Diagnostic Privacy Sanitizer
=========================================
Provides canonical redaction and sanitization for logs, diagnostic errors,
previews, tracebacks, IPC gateway DTOs, and quarantine records.
Remediates raw sensitive data exposure across AKAAL.
"""

import re
from typing import Any, Dict, List, Optional, Union

# Common sensitive parameter names
SENSITIVE_KEY_PATTERN = re.compile(
    r"(pass|password|pwd|secret|token|ssn|social_security|credit_card|card_num|cvv|api_key|private_key|auth|bearer)",
    re.IGNORECASE,
)

# Common regex patterns for raw values in text
EMAIL_REGEX = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
SSN_REGEX = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
CARD_REGEX = re.compile(r"\b(?:\d[ -]*?){13,16}\b")


class LogAndDiagnosticSanitizer:
    """Canonical Privacy Sanitizer for Logs, Errors, Preview, and Quarantine Evidence."""

    @classmethod
    def sanitize_text(cls, text: str) -> str:
        """Redacts raw email, SSN, and card patterns in plain text."""
        if not text or not isinstance(text, str):
            return text
        sanitized = EMAIL_REGEX.sub("[REDACTED_EMAIL]", text)
        sanitized = SSN_REGEX.sub("[REDACTED_SSN]", sanitized)
        sanitized = CARD_REGEX.sub("[REDACTED_CARD]", sanitized)
        return sanitized

    @classmethod
    def sanitize_dict(cls, data: Dict[str, Any], mask_keys: Optional[List[str]] = None) -> Dict[str, Any]:
        """Recursively redacts dictionary values matching sensitive keys or patterns."""
        if not isinstance(data, dict):
            return data

        custom_keys = set(mask_keys) if mask_keys else set()
        sanitized: Dict[str, Any] = {}

        for k, v in data.items():
            key_str = str(k)
            is_sensitive_key = bool(SENSITIVE_KEY_PATTERN.search(key_str)) or (key_str in custom_keys)

            if is_sensitive_key:
                if v is None:
                    sanitized[k] = None
                else:
                    sanitized[k] = "[REDACTED]"
            elif isinstance(v, dict):
                sanitized[k] = cls.sanitize_dict(v, mask_keys)
            elif isinstance(v, list):
                sanitized[k] = [cls.sanitize_dict(item, mask_keys) if isinstance(item, dict) else cls._sanitize_scalar(item) for item in v]
            elif isinstance(v, str):
                sanitized[k] = cls.sanitize_text(v)
            else:
                sanitized[k] = v

        return sanitized

    @classmethod
    def _sanitize_scalar(cls, val: Any) -> Any:
        if isinstance(val, str):
            return cls.sanitize_text(val)
        return val

    @classmethod
    def sanitize_quarantine_record(cls, record_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Redacts raw entity_key, reason, and error details in operator-visible quarantine records."""
        sanitized = dict(record_dict)
        if "entity_key" in sanitized and sanitized["entity_key"]:
            key_val = str(sanitized["entity_key"])
            # Keep table prefix if table:key format
            if ":" in key_val:
                parts = key_val.split(":", 1)
                sanitized["entity_key"] = f"{parts[0]}:[REDACTED_KEY]"
            else:
                sanitized["entity_key"] = "[REDACTED_KEY]"

        if "reason" in sanitized and isinstance(sanitized["reason"], str):
            sanitized["reason"] = cls.sanitize_text(sanitized["reason"])

        return cls.sanitize_dict(sanitized)

    @classmethod
    def sanitize_hook_parameters(cls, params: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Redacts sensitive values in hook parameters dict."""
        if not params or not isinstance(params, dict):
            return {}
        return cls.sanitize_dict(params)

    @classmethod
    def sanitize_sql_preview(cls, sql: str, params: Optional[Dict[str, Any]] = None) -> str:
        """Redacts secrets, raw credentials, and sensitive parameters from SQL string preview."""
        if not sql or not isinstance(sql, str):
            return ""
        sanitized_sql = cls.sanitize_text(sql)
        # Redact raw password assignments in SQL text e.g. IDENTIFIED BY 'secret', PASSWORD 'secret', WITH PASSWORD 'secret'
        sanitized_sql = re.sub(
            r"(IDENTIFIED\s+BY|SET\s+PASSWORD\s*=|WITH\s+PASSWORD|PASSWORD\s*=|\bPASSWORD)\s*['\"][^'\"]+['\"]",
            r"\1 '[REDACTED]'",
            sanitized_sql,
            flags=re.IGNORECASE,
        )
        sanitized_sql = re.sub(r"(SUPER_SECRET_[A-Z0-9_]+)", "[REDACTED_SECRET]", sanitized_sql)
        if params and isinstance(params, dict):
            for k, v in params.items():
                if v and isinstance(v, str) and len(v) > 3:
                    # If parameter key or value looks sensitive or contains secret payload
                    if SENSITIVE_KEY_PATTERN.search(str(k)) or "SECRET" in str(v).upper() or "TOKEN" in str(v).upper():
                        sanitized_sql = sanitized_sql.replace(v, "[REDACTED]")
        return sanitized_sql

    @classmethod
    def sanitize_hook_diagnostics(cls, text: str) -> str:
        """Redacts sensitive data from hook error messages and execution diagnostics."""
        if not text or not isinstance(text, str):
            return ""
        sanitized = cls.sanitize_text(text)
        sanitized = re.sub(r"(SUPER_SECRET_[A-Z0-9_]+)", "[REDACTED_SECRET]", sanitized)
        sanitized = re.sub(r"(password|secret|token|api_key)=['\"]?[^'\"]+['\"]?", r"\1=[REDACTED]", sanitized, flags=re.IGNORECASE)
        return sanitized

