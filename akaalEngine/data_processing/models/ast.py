"""
akaalEngine.data_processing.models.ast
=======================================
AST node representations for expressions and predicates in Authority #8.
Mined from `akaal/transformation/models.py`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Sequence


@dataclass(frozen=True)
class ASTNode:
    """Base immutable AST node."""
    pass


@dataclass(frozen=True)
class ColumnRefNode(ASTNode):
    """Refers to a column by name."""
    column_name: str


@dataclass(frozen=True)
class ConstantNode(ASTNode):
    """Constant value node."""
    value: Any


@dataclass(frozen=True)
class FunctionCallNode(ASTNode):
    """Function call AST node (e.g. CONCAT, UPPER, COALESCE)."""
    function_name: str
    args: Sequence[ASTNode] = field(default_factory=tuple)


@dataclass(frozen=True)
class ConditionalNode(ASTNode):
    """Conditional expression node (IF condition THEN true_branch ELSE false_branch)."""
    condition: ASTNode
    true_branch: ASTNode
    false_branch: ASTNode
