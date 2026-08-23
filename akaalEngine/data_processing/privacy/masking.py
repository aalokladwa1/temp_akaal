"""
akaalEngine.data_processing.privacy.masking
============================================
MaskingEngine implementing privacy strategies (redaction, hashing, HMAC pseudonymization, format-preserving masking).
Mined from `akaal/privacy/engine.py`.
"""

import hashlib
import hmac
import logging
from typing import Any, Callable, Optional

from akaalEngine.data_processing.models.plan import PrivacyStrategy

logger = logging.getLogger("akaalEngine.data_processing.privacy.masking")


class MaskingEngine:
    """Executes data masking and privacy strategies over column values."""

    @classmethod
    def apply_mask(
        cls,
        strategy: PrivacyStrategy,
        value: Any,
        mask_char: str = "*",
        unmasked_length: int = 4,
        secret_resolver: Optional[Callable[[str], bytes]] = None,
        key_ref: Optional[str] = None,
    ) -> Any:
        if value is None:
            return None

        val_str = str(value)

        if strategy == PrivacyStrategy.NULLIFY:
            return None

        elif strategy == PrivacyStrategy.STATIC_REDACT:
            return "[REDACTED]"

        elif strategy == PrivacyStrategy.PARTIAL_MASK:
            length = len(val_str)
            if length <= unmasked_length:
                return mask_char * length
            visible = val_str[-unmasked_length:]
            masked_part = mask_char * (length - unmasked_length)
            return masked_part + visible

        elif strategy == PrivacyStrategy.HASH:
            return hashlib.sha256(val_str.encode("utf-8")).hexdigest()

        elif strategy == PrivacyStrategy.KEYED_PSEUDONYM:
            hmac_key = secret_resolver(key_ref) if secret_resolver and key_ref else b"AKAAL-DEFAULT-PSEUDONYM-HMAC-KEY"
            h = hmac.new(hmac_key, val_str.encode("utf-8"), hashlib.sha256)
            return f"PSEUDO-{h.hexdigest()[:16].upper()}"

        elif strategy == PrivacyStrategy.FORMAT_PRESERVING_MASK:
            if "@" in val_str and "." in val_str:
                parts = val_str.split("@", 1)
                name = parts[0]
                domain_parts = parts[1].split(".", 1)
                dname = domain_parts[0]
                tld = domain_parts[1]
                masked_name = name[0] + (mask_char * (len(name) - 1)) if len(name) > 1 else mask_char
                masked_dname = dname[0] + (mask_char * (len(dname) - 1)) if len(dname) > 1 else mask_char
                return f"{masked_name}@{masked_dname}.{tld}"
            else:
                masked_chars = [mask_char if ch.isdigit() else ch for ch in val_str]
                return "".join(masked_chars)

        return val_str
