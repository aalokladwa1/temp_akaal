"""
Akaal — Oracle Rule Provider
============================
Built-in rule provider for Oracle target rules.
"""

from typing import List
from akaal.rulebook.providers.base_provider import BaseRuleProvider
from akaal.rulebook.models.rule import Rule, RuleCategory, RuleScope, RuleProvenance


class OracleRuleProvider(BaseRuleProvider):
    provider_id = "oracle_pack"
    provider_name = "Oracle Enterprise Rule Pack"
    provider_version = "1.0.0"
    target_engine = "ORACLE"

    def rules(self) -> List[Rule]:
        return [
            Rule(
                rule_id="ORA-VEND-001",
                name="Oracle 19c Compatibility Check",
                description="Enforce Oracle 19c parameters",
                category=RuleCategory.VENDOR,
                scope=RuleScope.GLOBAL,
                priority=1,
                provenance=RuleProvenance.VENDOR_PACK,
                action_payload={"engine": "ORACLE", "version": "19c"},
            ),
        ]
