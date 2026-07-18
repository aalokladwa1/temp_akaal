"""
Akaal — Canonical Function Registry
===================================
Universal function AST library standardizing scalar and aggregate functions.
"""

from typing import Dict, List, Optional
from akaal.decoder.models.canonical_expression import FunctionNode, ASTNode


class CanonicalFunctionRegistry:
    """Universal function AST library."""

    _functions: Dict[str, str] = {
        "abs": "ABS",
        "lower": "LOWER",
        "upper": "UPPER",
        "concat": "CONCAT",
        "length": "LENGTH",
        "trim": "TRIM",
        "substring": "SUBSTRING",
        "substr": "SUBSTRING",
        "round": "ROUND",
        "now": "NOW",
        "current_timestamp": "NOW",
        "coalesce": "COALESCE",
        "nvl": "COALESCE",
        "ifnull": "COALESCE",
    }

    @classmethod
    def resolve_function(cls, raw_func_name: str, arguments: Optional[List[ASTNode]] = None) -> FunctionNode:
        clean_name = raw_func_name.lower().strip()
        canonical_name = cls._functions.get(clean_name, raw_func_name.upper())
        return FunctionNode(function_name=canonical_name, arguments=arguments or [])
