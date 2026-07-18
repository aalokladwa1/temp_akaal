"""
Akaal — PostgreSQL Rule Provider
================================
Built-in rule provider for PostgreSQL target rules.
"""

from typing import List
from akaal.rulebook.providers.base_provider import BaseRuleProvider
from akaal.rulebook.models.rule import Rule, RuleCategory, RuleScope, RuleProvenance


class PostgresRuleProvider(BaseRuleProvider):
    provider_id = "postgres_pack"
    provider_name = "PostgreSQL Enterprise Rule Pack"
    provider_version = "1.0.0"
    target_engine = "POSTGRESQL"

    def rules(self) -> List[Rule]:
        return [
            Rule(
                rule_id="PG-VEND-001",
                name="PostgreSQL 15 Compatibility Check",
                description="Enforce PostgreSQL 15 dialect parameters",
                category=RuleCategory.VENDOR,
                scope=RuleScope.GLOBAL,
                priority=1,
                provenance=RuleProvenance.VENDOR_PACK,
                action_payload={"engine": "POSTGRESQL", "version": "15.0"},
            ),
            Rule(
                rule_id="PG-CONV-001",
                name="Oracle VARCHAR2 to VARCHAR Mapping",
                description="Map VARCHAR2 to VARCHAR in PostgreSQL",
                category=RuleCategory.CONVERSION,
                scope=RuleScope.GLOBAL,
                priority=15,
                provenance=RuleProvenance.VENDOR_PACK,
                action_payload={"source_type": "VARCHAR2", "target_type": "VARCHAR"},
            ),
            Rule(
                rule_id="PG-CONV-002",
                name="Oracle NUMBER to NUMERIC Mapping",
                description="Map NUMBER to NUMERIC in PostgreSQL",
                category=RuleCategory.CONVERSION,
                scope=RuleScope.GLOBAL,
                priority=15,
                provenance=RuleProvenance.VENDOR_PACK,
                action_payload={"source_type": "NUMBER", "target_type": "NUMERIC"},
            ),
        ]
