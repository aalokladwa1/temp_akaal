from dataclasses import dataclass
from akaal.migration.models import ObjectType

@dataclass(frozen=True)
class DriftRuleSpec:
    rule_id: str
    description: str
    target_object_type: ObjectType
