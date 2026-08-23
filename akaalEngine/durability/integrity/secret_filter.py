"""
Secret Redaction & Sanitization Filter for Authority #5 — Durability (DUR-015).
"""

import dataclasses
import re
from typing import Any, Dict, Set
from akaalEngine.durability.models.errors import DurabilityError


class SecretSanitizationFilter:
    """
    Mandatory pre-persistence filter establishing a three-tier security boundary:
    - Tier 1: Prohibited Authentication Material (passwords, secret keys, tokens, credentials, DSNs).
    - Tier 2: Permitted Operational Position Tokens (SCN, LSN, GTID, resume_token, continuation_token, offset).
    - Tier 3: Permitted Data Payload Spills (binary buffers written to bounded spooler files with restricted ACLs).
    """

    PROHIBITED_NORMALIZED_PATTERNS: Set[str] = {
        "password", "passwd", "pwd", "secret", "privatekey", "privkey", "secretkey",
        "apikey", "accesskey", "bearertoken", "authtoken", "authorization", "connectionstring",
        "credential", "clientsecret", "dsn"
    }

    PERMITTED_NORMALIZED_PATTERNS: Set[str] = {
        "providertoken", "continuationtoken", "resumetoken", "lsn", "scn",
        "gtid", "binlogposition", "partitionoffset", "recordoffset", "sequencenumber", "positiontoken"
    }

    @classmethod
    def _normalize_key(cls, k: str) -> str:
        return str(k).lower().replace("_", "").replace("-", "").replace(" ", "")

    @classmethod
    def contains_prohibited_secrets(cls, data: Any) -> bool:
        """Inspects arbitrary data structures for prohibited Tier 1 authentication credentials."""
        if dataclasses.is_dataclass(data) and not isinstance(data, type):
            data = dataclasses.asdict(data)

        if isinstance(data, dict):
            for k, v in data.items():
                norm_k = cls._normalize_key(str(k))

                # If key matches operational position tokens, skip key pattern check and inspect value
                if norm_k in cls.PERMITTED_NORMALIZED_PATTERNS:
                    if cls.contains_prohibited_secrets(v):
                        return True
                    continue

                # Check if normalized key matches any prohibited pattern
                if any(pattern in norm_k for pattern in cls.PROHIBITED_NORMALIZED_PATTERNS):
                    return True

                if cls.contains_prohibited_secrets(v):
                    return True
        elif isinstance(data, (list, tuple, set)):
            for item in data:
                if cls.contains_prohibited_secrets(item):
                    return True
        elif isinstance(data, str):
            data_lower = data.lower()
            if (
                "://" in data_lower and ("@" in data_lower or ":" in data_lower.split("://")[1])
            ) or "password=" in data_lower or "pwd=" in data_lower or "authorization: bearer" in data_lower:
                return True

        return False

    @classmethod
    def sanitize_state_dict(cls, data: Any) -> Any:
        """Validates input payload and raises DurabilityError if prohibited secrets are present."""
        if cls.contains_prohibited_secrets(data):
            raise DurabilityError("Prohibited Tier 1 authentication material detected in durability payload.")
        return data
