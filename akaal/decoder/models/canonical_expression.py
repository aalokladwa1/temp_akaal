"""
Akaal — Canonical Expression AST
================================
Immutable Abstract Syntax Tree (AST) node representations for vendor-neutral expression modeling.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ASTNode:
    """Base AST Node."""
    node_type: str = "ASTNode"

    def to_dict(self) -> Dict[str, Any]:
        return {"node_type": self.node_type}


@dataclass
class ConstantNode(ASTNode):
    value: Any = None
    data_type: str = "UNICODE_STRING"

    def __post_init__(self):
        self.node_type = "ConstantNode"

    def to_dict(self) -> Dict[str, Any]:
        return {"node_type": self.node_type, "value": self.value, "data_type": self.data_type}


@dataclass
class ColumnNode(ASTNode):
    column_name: str = ""
    table_name: Optional[str] = None
    schema_name: Optional[str] = None

    def __post_init__(self):
        self.node_type = "ColumnNode"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_type": self.node_type,
            "column_name": self.column_name,
            "table_name": self.table_name,
            "schema_name": self.schema_name,
        }


@dataclass
class FunctionNode(ASTNode):
    function_name: str = ""
    arguments: List[ASTNode] = field(default_factory=list)

    def __post_init__(self):
        self.node_type = "FunctionNode"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_type": self.node_type,
            "function_name": self.function_name,
            "arguments": [a.to_dict() for a in self.arguments],
        }


@dataclass
class OperatorNode(ASTNode):
    operator: str = "="
    left: Optional[ASTNode] = None
    right: Optional[ASTNode] = None

    def __post_init__(self):
        self.node_type = "OperatorNode"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_type": self.node_type,
            "operator": self.operator,
            "left": self.left.to_dict() if self.left else None,
            "right": self.right.to_dict() if self.right else None,
        }
