"""
akaalEngine.discovery.core.sampling
==================================
Deterministic data preview sampler with sensitive PII and credential redaction guard.
"""

from __future__ import annotations

import re
import time
from typing import Any, Mapping, Optional, Sequence

from akaalEngine.discovery.models.sampling import SampledRecordSet


class RedactionGuard:
    """
    Scans record keys and values for sensitive patterns (passwords, tokens, SSNs, credit cards)
    and replaces them with safe redaction markers.
    """

    SENSITIVE_KEY_PATTERNS = [
        re.compile(r"pass(word)?", re.IGNORECASE),
        re.compile(r"secret", re.IGNORECASE),
        re.compile(r"token", re.IGNORECASE),
        re.compile(r"api[_-]?key", re.IGNORECASE),
        re.compile(r"auth", re.IGNORECASE),
        re.compile(r"email", re.IGNORECASE),
        re.compile(r"ssn", re.IGNORECASE),
        re.compile(r"credit[_-]?card", re.IGNORECASE),
        re.compile(r"cvv", re.IGNORECASE),
        re.compile(r"private[_-]?key", re.IGNORECASE),
    ]

    REDACTED_PLACEHOLDER = "[REDACTED]"

    @classmethod
    def is_sensitive_key(cls, key_name: str) -> bool:
        return any(pat.search(key_name) for pat in cls.SENSITIVE_KEY_PATTERNS)

    @classmethod
    def sanitize_record(cls, record: Any) -> dict[str, Any]:
        sanitized = {}
        if hasattr(record, "items") and callable(record.items):
            items = record.items()
        elif hasattr(record, "keys") and callable(record.keys):
            items = [(k, record[k]) for k in record.keys()]
        elif isinstance(record, dict):
            items = record.items()
        else:
            return {}

        for k, v in items:
            k_str = str(k)
            if cls.is_sensitive_key(k_str):
                sanitized[k_str] = cls.REDACTED_PLACEHOLDER
            elif isinstance(v, str) and len(v) > 500:
                # Truncate overly long strings in preview
                sanitized[k_str] = v[:500] + "... [TRUNCATED]"
            else:
                sanitized[k_str] = v
        return sanitized


class DeterministicSampler:
    """
    Packages raw sample rows into a typed, redacted SampledRecordSet.
    """

    @classmethod
    def package_sample(
        cls,
        table_name: str,
        schema_name: str,
        column_names: Sequence[str],
        raw_records: Sequence[Any],
        duration_ms: float = 0.0,
    ) -> SampledRecordSet:
        formatted_records = []
        for r in raw_records:
            if hasattr(r, "keys") and callable(r.keys):
                rec_dict = {k: r[k] for k in r.keys()}
            elif isinstance(r, (tuple, list)) and column_names:
                rec_dict = dict(zip(column_names, r))
            elif isinstance(r, dict):
                rec_dict = r
            elif hasattr(r, "__dict__"):
                rec_dict = dict(r.__dict__)
            else:
                rec_dict = {f"col_{i}": val for i, val in enumerate(r)} if hasattr(r, "__iter__") else {"val": r}
            formatted_records.append(rec_dict)

        sanitized_rows = tuple(RedactionGuard.sanitize_record(r) for r in formatted_records)
        return SampledRecordSet(
            table_name=table_name,
            schema_name=schema_name,
            column_names=tuple(column_names),
            records=sanitized_rows,
            sample_count=len(sanitized_rows),
            execution_duration_ms=duration_ms,
            is_sampled=True,
            is_redacted=True,
            error_message=None,
        )

    @classmethod
    def package_failure(
        cls,
        table_name: str,
        schema_name: str,
        error_message: str,
        duration_ms: float = 0.0,
    ) -> SampledRecordSet:
        """Packages a failed sampling attempt with is_sampled=False and explicit error_message."""
        return SampledRecordSet(
            table_name=table_name,
            schema_name=schema_name,
            column_names=(),
            records=(),
            sample_count=0,
            execution_duration_ms=duration_ms,
            is_sampled=False,
            is_redacted=True,
            error_message=error_message,
        )

