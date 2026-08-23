"""
akaalEngine.schema.procedural.ast_nodes
=======================================
Advanced Object Intermediate Representation (AOIR) typed AST nodes for procedural SQL routines.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping, Optional, Sequence, Tuple

from akaalEngine.schema.models.programmables import ParameterMode, RoutineKind
from akaalEngine.schema.procedural.lexer import ParsedTokenRange, SourceLocation


@dataclass(frozen=True)
class AOIRNode:
    """Base abstract node in the AOIR typed AST hierarchy."""
    location: Optional[SourceLocation] = None
    token_range: Optional[ParsedTokenRange] = None


@dataclass(frozen=True)
class VariableDeclaration(AOIRNode):
    """Local variable, constant, or cursor record declaration."""
    name: str = ""
    data_type: str = ""
    default_value: Optional[str] = None
    is_constant: bool = False


@dataclass(frozen=True)
class ParameterDeclaration(AOIRNode):
    """Routine formal parameter declaration."""
    name: str = ""
    data_type: str = ""
    mode: ParameterMode = ParameterMode.IN
    default_value: Optional[str] = None


@dataclass(frozen=True)
class CursorDefinition(AOIRNode):
    """Explicit static cursor declaration."""
    name: str = ""
    query_sql: str = ""
    parameters: Tuple[ParameterDeclaration, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not isinstance(self.parameters, tuple):
            object.__setattr__(self, "parameters", tuple(self.parameters))


@dataclass(frozen=True)
class ExceptionHandler(AOIRNode):
    """Structured exception handling block (WHEN ... THEN ...)."""
    exception_names: Tuple[str, ...] = field(default_factory=tuple)  # e.g. ("NO_DATA_FOUND", "OTHERS")
    statements: Tuple[AOIRNode, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not isinstance(self.exception_names, tuple):
            object.__setattr__(self, "exception_names", tuple(self.exception_names))
        if not isinstance(self.statements, tuple):
            object.__setattr__(self, "statements", tuple(self.statements))


@dataclass(frozen=True)
class BlockNode(AOIRNode):
    """Procedural block with declarations, executable statements, and exception handlers."""
    declarations: Tuple[AOIRNode, ...] = field(default_factory=tuple)
    statements: Tuple[AOIRNode, ...] = field(default_factory=tuple)
    exception_handlers: Tuple[ExceptionHandler, ...] = field(default_factory=tuple)
    label: Optional[str] = None

    def __post_init__(self) -> None:
        for attr in ("declarations", "statements", "exception_handlers"):
            val = getattr(self, attr)
            if not isinstance(val, tuple):
                object.__setattr__(self, attr, tuple(val))


@dataclass(frozen=True)
class ElsifClause(AOIRNode):
    """ELSIF branch in conditional statements."""
    condition: str = ""
    statements: Tuple[AOIRNode, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not isinstance(self.statements, tuple):
            object.__setattr__(self, "statements", tuple(self.statements))


@dataclass(frozen=True)
class IfStatement(AOIRNode):
    """IF ... THEN ... ELSIF ... ELSE ... END IF statement."""
    condition: str = ""
    then_statements: Tuple[AOIRNode, ...] = field(default_factory=tuple)
    elsif_clauses: Tuple[ElsifClause, ...] = field(default_factory=tuple)
    else_statements: Tuple[AOIRNode, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        for attr in ("then_statements", "elsif_clauses", "else_statements"):
            val = getattr(self, attr)
            if not isinstance(val, tuple):
                object.__setattr__(self, attr, tuple(val))


@dataclass(frozen=True)
class WhenClause(AOIRNode):
    """WHEN branch in CASE statements."""
    condition: str = ""
    statements: Tuple[AOIRNode, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not isinstance(self.statements, tuple):
            object.__setattr__(self, "statements", tuple(self.statements))


@dataclass(frozen=True)
class CaseStatement(AOIRNode):
    """CASE statement with multiple WHEN clauses and optional ELSE."""
    expression: Optional[str] = None
    when_clauses: Tuple[WhenClause, ...] = field(default_factory=tuple)
    else_statements: Tuple[AOIRNode, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        for attr in ("when_clauses", "else_statements"):
            val = getattr(self, attr)
            if not isinstance(val, tuple):
                object.__setattr__(self, attr, tuple(val))


@dataclass(frozen=True)
class LoopStatement(AOIRNode):
    """Unbounded LOOP ... END LOOP statement."""
    statements: Tuple[AOIRNode, ...] = field(default_factory=tuple)
    label: Optional[str] = None

    def __post_init__(self) -> None:
        if not isinstance(self.statements, tuple):
            object.__setattr__(self, "statements", tuple(self.statements))


@dataclass(frozen=True)
class WhileStatement(AOIRNode):
    """WHILE ... LOOP ... END LOOP statement."""
    condition: str = ""
    statements: Tuple[AOIRNode, ...] = field(default_factory=tuple)
    label: Optional[str] = None

    def __post_init__(self) -> None:
        if not isinstance(self.statements, tuple):
            object.__setattr__(self, "statements", tuple(self.statements))


@dataclass(frozen=True)
class ForLoopStatement(AOIRNode):
    """Integer FOR i IN [REVERSE] lower..upper LOOP statement."""
    iterator_name: str = ""
    lower_bound: str = ""
    upper_bound: str = ""
    is_reverse: bool = False
    statements: Tuple[AOIRNode, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not isinstance(self.statements, tuple):
            object.__setattr__(self, "statements", tuple(self.statements))


@dataclass(frozen=True)
class CursorForLoopStatement(AOIRNode):
    """Cursor FOR rec IN cursor_name[(params)] / (SELECT ...) LOOP statement."""
    record_name: str = ""
    cursor_or_query: str = ""
    statements: Tuple[AOIRNode, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not isinstance(self.statements, tuple):
            object.__setattr__(self, "statements", tuple(self.statements))


@dataclass(frozen=True)
class AssignmentStatement(AOIRNode):
    """Variable assignment (target := expression / SET target = expression)."""
    target: str = ""
    expression: str = ""


@dataclass(frozen=True)
class ReturnStatement(AOIRNode):
    """RETURN [expression] statement."""
    expression: Optional[str] = None


@dataclass(frozen=True)
class CallStatement(AOIRNode):
    """Procedure or routine invocation."""
    routine_name: str = ""
    arguments: Tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not isinstance(self.arguments, tuple):
            object.__setattr__(self, "arguments", tuple(self.arguments))


@dataclass(frozen=True)
class NullStatement(AOIRNode):
    """NULL; / no-op statement."""
    pass


@dataclass(frozen=True)
class RaiseStatement(AOIRNode):
    """RAISE [exception] / RAISE_APPLICATION_ERROR statement."""
    exception_name: Optional[str] = None
    error_code: Optional[int] = None
    message: Optional[str] = None


@dataclass(frozen=True)
class CursorOpenStatement(AOIRNode):
    """OPEN cursor_name [(args)] statement."""
    cursor_name: str = ""
    arguments: Tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not isinstance(self.arguments, tuple):
            object.__setattr__(self, "arguments", tuple(self.arguments))


@dataclass(frozen=True)
class CursorFetchStatement(AOIRNode):
    """FETCH cursor_name INTO var1, var2 statement."""
    cursor_name: str = ""
    target_variables: Tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not isinstance(self.target_variables, tuple):
            object.__setattr__(self, "target_variables", tuple(self.target_variables))


@dataclass(frozen=True)
class CursorCloseStatement(AOIRNode):
    """CLOSE cursor_name statement."""
    cursor_name: str = ""


@dataclass(frozen=True)
class DMLStatement(AOIRNode):
    """Embedded SQL statement (SELECT INTO, INSERT, UPDATE, DELETE, MERGE)."""
    dml_type: str = "SELECT"  # SELECT, INSERT, UPDATE, DELETE, MERGE
    sql: str = ""
    into_variables: Tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not isinstance(self.into_variables, tuple):
            object.__setattr__(self, "into_variables", tuple(self.into_variables))


@dataclass(frozen=True)
class DynamicSQLNode(AOIRNode):
    """Dynamic SQL execution (EXECUTE IMMEDIATE / sp_executesql)."""
    sql_expression: str = ""
    into_variables: Tuple[str, ...] = field(default_factory=tuple)
    using_variables: Tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        for attr in ("into_variables", "using_variables"):
            val = getattr(self, attr)
            if not isinstance(val, tuple):
                object.__setattr__(self, attr, tuple(val))


@dataclass(frozen=True)
class AutonomousTxNode(AOIRNode):
    """PRAGMA AUTONOMOUS_TRANSACTION flag."""
    is_autonomous: bool = True


@dataclass(frozen=True)
class UnsupportedConstruct(AOIRNode):
    """Unrecognized or unconvertible procedural construct with exact source snippet."""
    construct_type: str = "UNKNOWN"
    raw_snippet: str = ""
    reason: str = ""


@dataclass(frozen=True)
class RoutineAST(AOIRNode):
    """Complete Abstract Syntax Tree for a Procedure, Function, or Trigger."""
    name: str = ""
    routine_type: RoutineKind = RoutineKind.PROCEDURE
    parameters: Tuple[ParameterDeclaration, ...] = field(default_factory=tuple)
    return_type: Optional[str] = None
    body: BlockNode = field(default_factory=BlockNode)
    is_autonomous: bool = False
    extra: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))

    def __post_init__(self) -> None:
        if not isinstance(self.parameters, tuple):
            object.__setattr__(self, "parameters", tuple(self.parameters))
        if not isinstance(self.extra, MappingProxyType):
            object.__setattr__(self, "extra", MappingProxyType(dict(self.extra)))


@dataclass(frozen=True)
class PackageAST(AOIRNode):
    """Complete Abstract Syntax Tree for an Oracle Package."""
    name: str = ""
    spec_routines: Tuple[RoutineAST, ...] = field(default_factory=tuple)
    body_routines: Tuple[RoutineAST, ...] = field(default_factory=tuple)
    state_variables: Tuple[VariableDeclaration, ...] = field(default_factory=tuple)
    extra: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))

    def __post_init__(self) -> None:
        for attr in ("spec_routines", "body_routines", "state_variables"):
            val = getattr(self, attr)
            if not isinstance(val, tuple):
                object.__setattr__(self, attr, tuple(val))
        if not isinstance(self.extra, MappingProxyType):
            object.__setattr__(self, "extra", MappingProxyType(dict(self.extra)))
