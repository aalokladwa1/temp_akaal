from dataclasses import dataclass

@dataclass(frozen=True)
class HealthCheckRuleSpec:
    rule_id: str
    description: str
    category: str  # CAPACITY, DEPENDENCY, COMPATIBILITY, STORAGE
