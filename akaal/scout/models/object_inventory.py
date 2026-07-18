"""
Akaal — Object Inventory Model
==============================
Structured model for non-table database objects (procedures, functions, triggers, sequences).
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class ObjectInventory:
    """Discovered database objects."""
    procedures: List[Dict[str, Any]] = field(default_factory=list)
    functions: List[Dict[str, Any]] = field(default_factory=list)
    triggers: List[Dict[str, Any]] = field(default_factory=list)
    sequences: List[Dict[str, Any]] = field(default_factory=list)
    custom_types: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "procedures": self.procedures,
            "functions": self.functions,
            "triggers": self.triggers,
            "sequences": self.sequences,
            "custom_types": self.custom_types,
        }
