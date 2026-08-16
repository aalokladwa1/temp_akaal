import logging
from typing import Any, Dict, List, Optional
from akaal.core.models.configuration import MaskingConfiguration, MaskingRule
from akaal.privacy.models import PrivacyPolicy, PrivacyRule as CanonicalPrivacyRule, PrivacyStrategy
from akaal.privacy.engine import PrivacyEngine, PrivacyEngineError

logger = logging.getLogger("akaal.migration.masking")

class MaskingPolicyError(Exception):
    pass

class DataMasker:
    def __init__(self, config: MaskingConfiguration) -> None:
        self.config = config
        self._engines: Dict[str, PrivacyEngine] = {}

    def _get_engine(self, table_name: str) -> PrivacyEngine:
        if table_name in self._engines:
            return self._engines[table_name]

        rules = self.config.policies.get(table_name, []) if self.config and self.config.policies else []
        canonical_rules: List[CanonicalPrivacyRule] = []

        for r in rules:
            strat_str = r.masking_strategy.upper()
            strat = PrivacyStrategy.STATIC_REDACT
            if strat_str == "REDACT":
                strat = PrivacyStrategy.STATIC_REDACT
            elif strat_str == "NULLIFY":
                strat = PrivacyStrategy.NULLIFY
            elif strat_str == "HASH":
                strat = PrivacyStrategy.HASH
            elif strat_str == "PARTIAL":
                strat = PrivacyStrategy.PARTIAL_MASK

            canonical_rules.append(
                CanonicalPrivacyRule(
                    rule_id=f"rule-{r.column_name}",
                    column_name=r.column_name,
                    strategy=strat,
                    salt=r.salt,
                    mask_char=r.mask_char if hasattr(r, "mask_char") and r.mask_char else "*",
                    unmasked_length=r.unmasked_length,
                    replacement_value=r.replacement_value,
                )
            )

        policy = PrivacyPolicy(object_name=table_name, rules=canonical_rules)
        engine = PrivacyEngine(policy)
        engine.compile_policy()
        self._engines[table_name] = engine
        return engine

    def validate_policies(self) -> None:
        """Validates all registered masking policies by building canonical PrivacyEngine."""
        if not self.config or not self.config.policies:
            return
        for table in self.config.policies.keys():
            self._get_engine(table)

    def mask_row(self, table_name: str, row: Dict[str, Any]) -> Dict[str, Any]:
        """Delegates masking execution to canonical PrivacyEngine."""
        if not self.config or not self.config.policies:
            return row
        engine = self._get_engine(table_name)
        return engine.transform_row(row)
