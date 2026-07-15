from dataclasses import dataclass
from typing import Set
from akaal.migration.models import ObjectType
from akaal.migration.reliability.models.risk import RiskLevel

@dataclass(frozen=True)
class ValidationRuleSpec:
    rule_id: str
    description: str
    target_objects: Set[ObjectType]
    severity: RiskLevel
