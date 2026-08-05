"""
AKAAL PL/SQL Transpiler — AST Node Definitions
================================================
Represents Abstract Syntax Tree nodes for Oracle PL/SQL stored procedure, function, trigger, and package constructs.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ASTNode:
    line_number: int = 1


@dataclass
class ParameterNode(ASTNode):
    name: str = ""
    mode: str = "IN"  # IN, OUT, INOUT
    data_type: str = "VARCHAR"
    default_value: Optional[str] = None


@dataclass
class VariableDeclNode(ASTNode):
    name: str = ""
    data_type: str = "VARCHAR"
    is_constant: bool = False
    initial_value: Optional[str] = None


@dataclass
class StatementNode(ASTNode):
    raw_code: str = ""


@dataclass
class ProcedureNode(ASTNode):
    name: str = ""
    parameters: List[ParameterNode] = field(default_factory=list)
    variables: List[VariableDeclNode] = field(default_factory=list)
    body_statements: List[str] = field(default_factory=list)
    exception_handlers: List[Dict[str, str]] = field(default_factory=list)


@dataclass
class FunctionNode(ASTNode):
    name: str = ""
    parameters: List[ParameterNode] = field(default_factory=list)
    return_type: str = "VARCHAR"
    variables: List[VariableDeclNode] = field(default_factory=list)
    body_statements: List[str] = field(default_factory=list)
    exception_handlers: List[Dict[str, str]] = field(default_factory=list)


@dataclass
class TriggerNode(ASTNode):
    name: str = ""
    table_name: str = ""
    timing: str = "BEFORE"  # BEFORE, AFTER, INSTEAD OF
    events: List[str] = field(default_factory=lambda: ["INSERT", "UPDATE"])
    for_each_row: bool = True
    body_statements: List[str] = field(default_factory=list)


@dataclass
class PackageNode(ASTNode):
    name: str = ""
    procedures: List[ProcedureNode] = field(default_factory=list)
    functions: List[FunctionNode] = field(default_factory=list)
