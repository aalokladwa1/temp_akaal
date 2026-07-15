from dataclasses import dataclass

@dataclass(frozen=True)
class SimulationRuleSpec:
    rule_id: str
    description: str
    target_estimator: str
