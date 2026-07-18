"""
Akaal — Base Rule Class
=======================
Base class for all specific rule definitions across the 7 rule categories.
"""

from akaal.rulebook.models.rule import Rule, RuleCategory, RuleScope, RuleProvenance, RuleCapabilityMetadata


class BaseRule(Rule):
    """Base rule class providing convenient initialization defaults."""

    def __init__(
        self,
        rule_id: str,
        name: str,
        description: str,
        category: RuleCategory,
        scope: RuleScope = RuleScope.GLOBAL,
        priority: int = 100,
        provenance: RuleProvenance = RuleProvenance.VENDOR_PACK,
        **kwargs,
    ):
        super().__init__(
            rule_id=rule_id,
            name=name,
            description=description,
            category=category,
            scope=scope,
            priority=priority,
            provenance=provenance,
            **kwargs,
        )
