"""
Akaal — MongoDB Rule Provider
=============================
Built-in rule provider for MongoDB target rules.
"""

from typing import List
from akaal.rulebook.providers.base_provider import BaseRuleProvider
from akaal.rulebook.models.rule import Rule, RuleCategory, RuleScope, RuleProvenance


class MongoDBRuleProvider(BaseRuleProvider):
    provider_id = "mongodb_pack"
    provider_name = "MongoDB Enterprise Rule Pack"
    provider_version = "1.0.0"
    target_engine = "MONGODB"

    def rules(self) -> List[Rule]:
        return [
            Rule(
                rule_id="MG-VEND-001",
                name="MongoDB 6.0 Document Rules",
                description="Enforce MongoDB BSON document rules",
                category=RuleCategory.VENDOR,
                scope=RuleScope.GLOBAL,
                priority=1,
                provenance=RuleProvenance.VENDOR_PACK,
                action_payload={"engine": "MONGODB", "version": "6.0"},
            ),
        ]
