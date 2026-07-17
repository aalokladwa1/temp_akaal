import hashlib
import logging
from typing import Any, Dict, List, Optional
from akaal.core.models.configuration import MaskingConfiguration, MaskingRule

logger = logging.getLogger("akaal.migration.masking")

class MaskingPolicyError(Exception):
    pass

class DataMasker:
    def __init__(self, config: MaskingConfiguration) -> None:
        self.config = config

    def validate_policies(self) -> None:
        """Validates all registered masking policies."""
        if not self.config or not self.config.policies:
            return
        for table, rules in self.config.policies.items():
            for rule in rules:
                strat = rule.masking_strategy.upper()
                if strat not in ("REDACT", "HASH", "PARTIAL", "NULLIFY"):
                    raise MaskingPolicyError(f"Unsupported masking strategy '{rule.masking_strategy}' for column '{rule.column_name}'.")
                if strat == "PARTIAL" and rule.unmasked_length < 0:
                    raise MaskingPolicyError(f"Invalid partial unmasked length for column '{rule.column_name}'.")

    def mask_row(self, table_name: str, row: Dict[str, Any]) -> Dict[str, Any]:
        """Applies masking rules, logging audit summaries."""
        if not self.config or not self.config.policies:
            return row
        rules = self.config.policies.get(table_name, [])
        if not rules:
            return row

        new_row = dict(row)
        masked_count = 0

        for rule in rules:
            col = rule.column_name
            if col not in new_row or new_row[col] is None:
                continue

            strat = rule.masking_strategy.upper()
            val = str(new_row[col])

            if strat == "REDACT":
                new_row[col] = rule.replacement_value or "[REDACTED]"
                masked_count += 1
            elif strat == "NULLIFY":
                new_row[col] = None
                masked_count += 1
            elif strat == "HASH":
                salt = rule.salt or ""
                payload = val + salt
                new_row[col] = hashlib.sha256(payload.encode("utf-8")).hexdigest()
                masked_count += 1
            elif strat == "PARTIAL":
                length = len(val)
                unmasked = rule.unmasked_length
                if length <= unmasked:
                    new_row[col] = rule.mask_char * length
                else:
                    visible = val[-unmasked:]
                    masked_part = rule.mask_char * (length - unmasked)
                    new_row[col] = masked_part + visible
                masked_count += 1

        if masked_count > 0:
            logger.debug(
                "[Masking Audit] Table '%s': Masked %d columns in row.",
                table_name, masked_count
            )

        return new_row
