"""
Akaal — MySQL Rule Provider
===========================
Built-in rule provider for MySQL target rules.
"""

from typing import List
from akaal.rulebook.providers.base_provider import BaseRuleProvider
from akaal.rulebook.models.rule import Rule, RuleCategory, RuleScope, RuleProvenance


class MySQLRuleProvider(BaseRuleProvider):
    provider_id = "mysql_pack"
    provider_name = "MySQL Enterprise Rule Pack"
    provider_version = "1.0.0"
    target_engine = "MYSQL"

    def rules(self) -> List[Rule]:
        return [
            Rule(
                rule_id="MY-VEND-001",
                name="MySQL 8.0 Compatibility Check",
                description="Enforce MySQL 8.0 InnoDB settings",
                category=RuleCategory.VENDOR,
                scope=RuleScope.GLOBAL,
                priority=1,
                provenance=RuleProvenance.VENDOR_PACK,
                action_payload={"engine": "MYSQL", "version": "8.0"},
            ),
        ]
