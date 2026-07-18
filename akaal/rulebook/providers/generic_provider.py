"""
Akaal — Generic Rule Provider
=============================
Default built-in provider exposing standard migration rules.
"""

from typing import List
from akaal.rulebook.providers.base_provider import BaseRuleProvider
from akaal.rulebook.models.rule import Rule, RuleCategory, RuleScope, RuleProvenance


class GenericRuleProvider(BaseRuleProvider):
    provider_id = "generic_pack"
    provider_name = "Generic Default Rule Pack"
    provider_version = "1.0.0"
    target_engine = "GENERIC"

    def rules(self) -> List[Rule]:
        return [
            Rule(
                rule_id="GEN-NAM-001",
                name="Lowercase Identifier Normalization",
                description="Normalize table and column identifiers to lowercase",
                category=RuleCategory.NAMING,
                scope=RuleScope.GLOBAL,
                priority=10,
                provenance=RuleProvenance.VENDOR_PACK,
                action_payload={"strategy": "LOWERCASE"},
            ),
            Rule(
                rule_id="GEN-CONV-001",
                name="Standard Data Type Fallback",
                description="Map unhandled data types to VARCHAR(255)",
                category=RuleCategory.CONVERSION,
                scope=RuleScope.GLOBAL,
                priority=20,
                provenance=RuleProvenance.VENDOR_PACK,
                action_payload={"fallback_type": "VARCHAR(255)"},
            ),
        ]
