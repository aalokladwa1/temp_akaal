"""
AKAAL Canonical Privacy Engine
==============================
Executes privacy policies across bulk migration batches, CDC event streams,
validation consistency checks, and backend preview.
Supports static redaction, partial masking, salted hashing, keyed HMAC pseudonymization,
durable tokenization, format-preserving masking, and nullification.
"""

import hmac
import hashlib
import logging
import re
from typing import Any, Dict, List, Optional, Tuple, Union

from akaal.privacy.models import (
    PrivacyPolicy,
    PrivacyRule,
    PrivacyStrategy,
    CompiledPrivacyPolicy,
)
from akaal.privacy.token_vault import ITokenVaultProvider, CentralStateStoreTokenVault
from akaal.privacy.sanitizer import LogAndDiagnosticSanitizer
from akaal.core.credential_vault import credential_vault

logger = logging.getLogger("akaal.privacy.engine")


class PrivacyEngineError(Exception):
    """Base exception for Privacy Engine operations."""
    pass


class PrivacyEngine:
    """Canonical Privacy Authority for AKAAL Enterprise Platform."""

    def __init__(
        self,
        policy: PrivacyPolicy,
        token_vault: Optional[ITokenVaultProvider] = None,
    ) -> None:
        self.policy = policy
        self.token_vault = token_vault or CentralStateStoreTokenVault()
        self._compiled: Optional[CompiledPrivacyPolicy] = None

    def compile_policy(self) -> CompiledPrivacyPolicy:
        """Compiles PrivacyPolicy and computes deterministic SHA-256 fingerprint."""
        sorted_rules = sorted(self.policy.rules, key=lambda r: (r.priority, r.column_name))
        fp = CompiledPrivacyPolicy.compute_fingerprint(self.policy.object_name, sorted_rules)
        self._compiled = CompiledPrivacyPolicy(
            object_name=self.policy.object_name,
            rules=sorted_rules,
            fingerprint=fp,
        )
        return self._compiled

    def _get_hmac_key(self, key_id: Optional[str]) -> bytes:
        target_key_id = key_id or "default-hmac-pseudonym-key"
        try:
            creds = credential_vault.get_credentials(target_key_id, fail_closed=False)
            raw_key_str = creds.get("password") if isinstance(creds, dict) else None
        except Exception:
            raw_key_str = None

        if not raw_key_str:
            raw_key_str = f"AKAAL-PSEUDONYM-HMAC-KEY-{target_key_id}"

        return raw_key_str.encode("utf-8")

    def _apply_rule(self, rule: PrivacyRule, value: Any) -> Any:
        if value is None:
            return None

        val_str = str(value)
        strat = rule.strategy

        if strat == PrivacyStrategy.NULLIFY:
            return None

        if strat == PrivacyStrategy.STATIC_REDACT:
            return rule.replacement_value or "[REDACTED]"

        if strat == PrivacyStrategy.PARTIAL_MASK:
            length = len(val_str)
            unmasked = rule.unmasked_length
            mask_char = rule.mask_char or "*"
            if length <= unmasked:
                return mask_char * length
            visible = val_str[-unmasked:]
            masked_part = mask_char * (length - unmasked)
            return masked_part + visible

        if strat == PrivacyStrategy.HASH:
            salt = rule.salt or ""
            payload = val_str + salt
            return hashlib.sha256(payload.encode("utf-8")).hexdigest()

        if strat == PrivacyStrategy.KEYED_PSEUDONYM:
            hmac_key = self._get_hmac_key(rule.key_id)
            domain_prefix = rule.privacy_domain or "DEFAULT_DOMAIN"
            payload_str = f"{domain_prefix}:{val_str}"
            h = hmac.new(hmac_key, payload_str.encode("utf-8"), hashlib.sha256)
            return f"PSEUDO-{h.hexdigest()[:16].upper()}"

        if strat == PrivacyStrategy.TOKENIZE:
            domain = rule.privacy_domain or "DEFAULT_TOKEN_DOMAIN"
            return self.token_vault.tokenize(val_str, domain, rule.key_id)

        if strat == PrivacyStrategy.FORMAT_PRESERVING_MASK:
            return self._format_preserving_mask(val_str, rule.mask_char or "*")

        return val_str

    def _format_preserving_mask(self, val_str: str, mask_char: str) -> str:
        # Email format preserving: a***@e***.com
        if "@" in val_str and "." in val_str:
            parts = val_str.split("@", 1)
            name = parts[0]
            domain_parts = parts[1].split(".", 1)
            dname = domain_parts[0]
            tld = domain_parts[1]
            masked_name = name[0] + (mask_char * (len(name) - 1)) if len(name) > 1 else mask_char
            masked_dname = dname[0] + (mask_char * (len(dname) - 1)) if len(dname) > 1 else mask_char
            return f"{masked_name}@{masked_dname}.{tld}"

        # Card / Number format preserving: preserve punctuation, mask digits
        masked_chars = []
        for ch in val_str:
            if ch.isdigit():
                masked_chars.append(mask_char)
            else:
                masked_chars.append(ch)
        return "".join(masked_chars)

    def transform_row(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """Applies compiled PrivacyPolicy rules to target row dictionary."""
        if not self.policy.rules:
            return dict(row)

        compiled = self._compiled or self.compile_policy()
        new_row = dict(row)

        for rule in compiled.rules:
            col = rule.column_name
            if col in new_row and new_row[col] is not None:
                try:
                    new_row[col] = self._apply_rule(rule, new_row[col])
                except Exception as exc:
                    logger.error(
                        f"[PRIVACY FAILURE] Rule '{rule.rule_id}' on column '{col}' failed: "
                        f"{LogAndDiagnosticSanitizer.sanitize_text(str(exc))}"
                    )
                    raise PrivacyEngineError(f"PRIVACY_RULE_FAILED: Rule '{rule.rule_id}' failed for column '{col}'.")

        return new_row

    def transform_batch(self, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Applies PrivacyEngine to a batch of target rows."""
        return [self.transform_row(r) for r in rows]

    def transform_cdc_event(self, cdc_event: Dict[str, Any]) -> Dict[str, Any]:
        """Applies PrivacyEngine to CDC event images while preserving primary key CDC identity."""
        if not isinstance(cdc_event, dict):
            return cdc_event

        new_event = dict(cdc_event)
        if "after_image" in new_event and isinstance(new_event["after_image"], dict):
            new_event["after_image"] = self.transform_row(new_event["after_image"])
        if "before_image" in new_event and isinstance(new_event["before_image"], dict):
            new_event["before_image"] = self.transform_row(new_event["before_image"])

        return new_event

    def preview_privacy(self, sample_rows: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Performs safe backend preview with ZERO target writes and sanitized before inputs."""
        compiled = self._compiled or self.compile_policy()
        transformed = self.transform_batch(sample_rows)

        sanitized_samples = [LogAndDiagnosticSanitizer.sanitize_dict(r) for r in sample_rows]
        sanitized_transformed = [LogAndDiagnosticSanitizer.sanitize_dict(r) for r in transformed]

        return {
            "status": "SUCCESS",
            "object_name": self.policy.object_name,
            "fingerprint": compiled.fingerprint,
            "rules_applied": len(compiled.rules),
            "sample_rows_before": sanitized_samples,
            "transformed_rows_after": sanitized_transformed,
        }
