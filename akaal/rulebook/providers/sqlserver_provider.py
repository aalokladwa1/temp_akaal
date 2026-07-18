"""
Akaal — SQL Server Rule Provider
================================
Built-in rule provider for SQL Server target rules.
"""

from typing import List
from akaal.rulebook.providers.base_provider import BaseRuleProvider
from akaal.rulebook.models.rule import Rule, RuleCategory, RuleScope, RuleProvenance


class SQLServerRuleProvider(BaseRuleProvider):
    provider_id = "sqlserver_pack"
    provider_name = "SQL Server Enterprise Rule Pack"
    provider_version = "1.0.0"
    target_engine = "SQLSERVER"

    def rules(self) -> List[Rule]:
        return [
            Rule(
                rule_id="MS-VEND-001",
                name="SQL Server 2022 Compatibility Check",
                description="Enforce SQL Server 2022 parameters",
                category=RuleCategory.VENDOR,
                scope=RuleScope.GLOBAL,
                priority=1,
                provenance=RuleProvenance.VENDOR_PACK,
                action_payload={"engine": "SQLSERVER", "version": "2022"},
            ),
        ]
