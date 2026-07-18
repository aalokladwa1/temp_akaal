"""
Akaal — Expression AST Engine
=============================
Single-responsibility engine building Expression AST node structures from default expressions and constraints.
"""

from typing import Dict, Any, Optional
from akaal.decoder.models.canonical_expression import ASTNode, ConstantNode, FunctionNode
from akaal.decoder.registry.canonical_function_registry import CanonicalFunctionRegistry


class ExpressionEngine:
    """Builds vendor-neutral Expression AST nodes."""

    def parse_expression(self, raw_expression: str) -> ASTNode:
        if not raw_expression:
            return ConstantNode(value=None, data_type="UNICODE_STRING")

        clean = raw_expression.strip().lower()

        if clean in ("now()", "current_timestamp", "sysdate", "getdate()"):
            return CanonicalFunctionRegistry.resolve_function("now")
        elif clean.isdigit():
            return ConstantNode(value=int(clean), data_type="INTEGER")
        elif clean in ("true", "false"):
            return ConstantNode(value=(clean == "true"), data_type="BOOLEAN")

        return ConstantNode(value=raw_expression, data_type="UNICODE_STRING")
