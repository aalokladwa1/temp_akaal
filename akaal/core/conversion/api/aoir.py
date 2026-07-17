"""
Akaal — Advanced-Object Intermediate Representation (AOIR)
===========================================================
Defines the shared, deeply immutable, fully-typed AST and semantic models
representing procedural code objects (Procedures, Functions, etc.).
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Tuple, Optional

class RoutineKind(str, Enum):
    PROCEDURE = "PROCEDURE"
    FUNCTION = "FUNCTION"

class ParameterMode(str, Enum):
    IN = "IN"
    OUT = "OUT"
    INOUT = "INOUT"

@dataclass(frozen=True)
class SourceLocation:
    line: int
    column: int
    offset: int

@dataclass(frozen=True)
class ParsedTokenRange:
    start: SourceLocation
    end: SourceLocation
    raw_text: str

@dataclass(frozen=True)
class MetadataPair:
    key: str
    value: str

@dataclass(frozen=True)
class RoutineParameter:
    name: str
    data_type: str
    mode: ParameterMode
    source_range: ParsedTokenRange
    default_expression: Optional[str] = None

@dataclass(frozen=True)
class ReturnSpecification:
    data_type: str
    is_table_type: bool
    source_range: ParsedTokenRange

class VolatilitySemantics(str, Enum):
    IMMUTABLE = "IMMUTABLE"
    STABLE = "STABLE"
    VOLATILE = "VOLATILE"

class SecurityExecutionContext(str, Enum):
    DEFINER = "DEFINER"
    INVOKER = "INVOKER"

class TransactionBehavior(str, Enum):
    SEMANTICALLY_EQUIVALENT = "SEMANTICALLY_EQUIVALENT"
    EQUIVALENT_WITH_ORCHESTRATION_CHANGE = "EQUIVALENT_WITH_ORCHESTRATION_CHANGE"
    REQUIRES_AUTONOMOUS_TRANSACTION_PROVIDER = "REQUIRES_AUTONOMOUS_TRANSACTION_PROVIDER"
    REQUIRES_MANUAL_REWRITE = "REQUIRES_MANUAL_REWRITE"
    UNSUPPORTED = "UNSUPPORTED"

@dataclass(frozen=True)
class ExceptionHandler:
    exception_name: str
    statement_range: ParsedTokenRange
    handler_body_range: ParsedTokenRange

@dataclass(frozen=True)
class CursorDefinition:
    name: str
    select_query_range: ParsedTokenRange
    is_scrollable: bool

@dataclass(frozen=True)
class DynamicSQLNode:
    query_expression_range: ParsedTokenRange
    using_parameters: Tuple[str, ...]

@dataclass(frozen=True)
class DependencyReference:
    object_name: str
    object_type: str
    source_range: ParsedTokenRange

@dataclass(frozen=True)
class ControlFlowGraph:
    nodes: Tuple[str, ...]
    edges: Tuple[Tuple[str, str], ...]

@dataclass(frozen=True)
class UnsupportedConstruct:
    construct_type: str
    source_range: ParsedTokenRange
    description: str

@dataclass(frozen=True)
class SemanticRisk:
    risk_level: str
    description: str
    remediation: str

@dataclass(frozen=True)
class MigrationAction:
    action_id: str
    action_type: str
    target_object_name: str
    parameters: Tuple[MetadataPair, ...]

@dataclass(frozen=True)
class ManualReviewRequirement:
    reason_code: str
    description: str
    source_range: ParsedTokenRange

@dataclass(frozen=True)
class AOIRNode:
    """The root AST node representing a compiled stored routine schema."""
    name: str
    kind: RoutineKind
    signature_range: ParsedTokenRange
    body_range: ParsedTokenRange
    parameters: Tuple[RoutineParameter, ...]
    return_spec: Optional[ReturnSpecification]
    local_variables: Tuple[RoutineParameter, ...]
    exception_handlers: Tuple[ExceptionHandler, ...]
    cursors: Tuple[CursorDefinition, ...]
    dynamic_sql_nodes: Tuple[DynamicSQLNode, ...]
    dependencies: Tuple[DependencyReference, ...]
    control_flow: Optional[ControlFlowGraph]
    unsupported_constructs: Tuple[UnsupportedConstruct, ...]
    volatility: VolatilitySemantics = VolatilitySemantics.VOLATILE
    security_context: SecurityExecutionContext = SecurityExecutionContext.INVOKER
    transaction_behavior: TransactionBehavior = TransactionBehavior.SEMANTICALLY_EQUIVALENT
    source_text: str = ""
    aoir_version: str = "1.0.0"
    source_dialect: str = ""
    target_dialect: str = ""
    routine_type: str = ""
    metadata: dict = field(default_factory=dict)

