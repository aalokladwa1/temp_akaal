"""
Akaal — Canonical Constraint Language
=====================================
Vendor-neutral database constraint language representations.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ConstraintType(str, Enum):
    PRIMARY_KEY = "PRIMARY_KEY"
    FOREIGN_KEY = "FOREIGN_KEY"
    UNIQUE = "UNIQUE"
    CHECK = "CHECK"
    GENERATED_VALUE = "GENERATED_VALUE"


class ReferenceAction(str, Enum):
    NO_ACTION = "NO_ACTION"
    RESTRICT = "RESTRICT"
    CASCADE = "CASCADE"
    SET_NULL = "SET_NULL"
    SET_DEFAULT = "SET_DEFAULT"


class ValidationState(str, Enum):
    VALIDATED = "VALIDATED"
    NOT_VALIDATED = "NOT_VALIDATED"


@dataclass
class CanonicalConstraint:
    constraint_name: str
    constraint_type: ConstraintType
    table_name: str
    schema_name: str = "public"
    columns: List[str] = field(default_factory=list)
    referenced_table: Optional[str] = None
    referenced_columns: List[str] = field(default_factory=list)
    on_delete: ReferenceAction = ReferenceAction.NO_ACTION
    on_update: ReferenceAction = ReferenceAction.NO_ACTION
    check_expression: Optional[Dict[str, Any]] = None
    validation_state: ValidationState = ValidationState.VALIDATED

    def to_dict(self) -> Dict[str, Any]:
        return {
            "constraint_name": self.constraint_name,
            "constraint_type": self.constraint_type.value if hasattr(self.constraint_type, "value") else str(self.constraint_type),
            "table_name": self.table_name,
            "schema_name": self.schema_name,
            "columns": self.columns,
            "referenced_table": self.referenced_table,
            "referenced_columns": self.referenced_columns,
            "on_delete": self.on_delete.value if hasattr(self.on_delete, "value") else str(self.on_delete),
            "on_update": self.on_update.value if hasattr(self.on_update, "value") else str(self.on_update),
            "check_expression": self.check_expression,
            "validation_state": self.validation_state.value if hasattr(self.validation_state, "value") else str(self.validation_state),
        }
