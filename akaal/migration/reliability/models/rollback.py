from dataclasses import dataclass

@dataclass(frozen=True)
class RollbackRuleSpec:
    rule_id: str
    description: str
    strategy_name: str
