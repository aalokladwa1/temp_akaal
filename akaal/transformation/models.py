"""
AKAAL Transformation & Data Cleansing Domain Models.
===================================================
Defines canonical dataclasses, AST expression nodes, cleansing policies,
and compiled transformation plan artifacts.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Any, Optional, Union, Set
import hashlib
import json


class RuleType(str, Enum):
    CLEANSING = "CLEANSING"
    EXPRESSION = "EXPRESSION"
    DEFAULT = "DEFAULT"
    TYPE_CONVERSION = "TYPE_CONVERSION"
    DERIVED = "DERIVED"
    LOOKUP = "LOOKUP"


class MalformedDataPolicy(str, Enum):
    FAIL_JOB = "FAIL_JOB"
    FAIL_OBJECT = "FAIL_OBJECT"
    REJECT_ROW = "REJECT_ROW"
    QUARANTINE_ROW = "QUARANTINE_ROW"
    USE_DEFAULT = "USE_DEFAULT"
    USE_NULL = "USE_NULL"


class MissingKeyPolicy(str, Enum):
    FAIL_ROW = "FAIL_ROW"
    QUARANTINE_ROW = "QUARANTINE_ROW"
    USE_DEFAULT = "USE_DEFAULT"
    PRESERVE_ORIGINAL = "PRESERVE_ORIGINAL"
    USE_NULL = "USE_NULL"


class DiagnosticLevel(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    BLOCKER = "BLOCKER"


@dataclass
class TransformationDiagnostic:
    level: DiagnosticLevel
    code: str
    message: str
    column_name: Optional[str] = None
    rule_id: Optional[str] = None


@dataclass
class ASTNode:
    """Base class for type-safe AST nodes (NO eval/exec allowed)."""
    node_type: str

    def to_dict(self) -> Dict[str, Any]:
        return {"node_type": self.node_type}


@dataclass
class LiteralNode(ASTNode):
    value: Any
    data_type: str = "string"

    def __init__(self, value: Any, data_type: str = "string"):
        super().__init__(node_type="LITERAL")
        self.value = value
        self.data_type = data_type

    def to_dict(self) -> Dict[str, Any]:
        return {"node_type": "LITERAL", "value": self.value, "data_type": self.data_type}


@dataclass
class ColumnRefNode(ASTNode):
    column_name: str

    def __init__(self, column_name: str):
        super().__init__(node_type="COLUMN_REF")
        self.column_name = column_name

    def to_dict(self) -> Dict[str, Any]:
        return {"node_type": "COLUMN_REF", "column_name": self.column_name}


@dataclass
class FunctionCallNode(ASTNode):
    function_name: str
    args: List[ASTNode] = field(default_factory=list)

    def __init__(self, function_name: str, args: List[ASTNode]):
        super().__init__(node_type="FUNCTION_CALL")
        self.function_name = function_name.upper()
        self.args = args

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_type": "FUNCTION_CALL",
            "function_name": self.function_name,
            "args": [arg.to_dict() for arg in self.args],
        }


@dataclass
class ConditionalNode(ASTNode):
    condition: ASTNode
    true_branch: ASTNode
    false_branch: ASTNode

    def __init__(self, condition: ASTNode, true_branch: ASTNode, false_branch: ASTNode):
        super().__init__(node_type="CONDITIONAL")
        self.condition = condition
        self.true_branch = true_branch
        self.false_branch = false_branch

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_type": "CONDITIONAL",
            "condition": self.condition.to_dict(),
            "true_branch": self.true_branch.to_dict(),
            "false_branch": self.false_branch.to_dict(),
        }


@dataclass
class LookupDefinition:
    lookup_name: str
    mapping_dictionary: Dict[str, Any] = field(default_factory=dict)
    missing_policy: MissingKeyPolicy = MissingKeyPolicy.PRESERVE_ORIGINAL
    default_value: Any = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "lookup_name": self.lookup_name,
            "mapping_dictionary": self.mapping_dictionary,
            "missing_policy": self.missing_policy.value,
            "default_value": self.default_value,
        }


@dataclass
class TransformationRule:
    rule_id: str
    column_name: str
    rule_type: RuleType = RuleType.EXPRESSION
    expression_ast: Optional[ASTNode] = None
    expression_text: Optional[str] = None
    default_value: Any = None
    target_type: Optional[str] = None
    priority: int = 10
    malformed_policy: MalformedDataPolicy = MalformedDataPolicy.USE_NULL
    lookup_definition: Optional[LookupDefinition] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "column_name": self.column_name,
            "rule_type": self.rule_type.value,
            "expression_ast": self.expression_ast.to_dict() if self.expression_ast else None,
            "expression_text": self.expression_text,
            "default_value": self.default_value,
            "target_type": self.target_type,
            "priority": self.priority,
            "malformed_policy": self.malformed_policy.value,
            "lookup_definition": self.lookup_definition.to_dict() if self.lookup_definition else None,
        }


@dataclass
class TransformationDefinition:
    object_name: str
    rules: List[TransformationRule] = field(default_factory=list)
    lookups: Dict[str, LookupDefinition] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "object_name": self.object_name,
            "rules": [r.to_dict() for r in self.rules],
            "lookups": {k: v.to_dict() for k, v in self.lookups.items()},
        }


@dataclass
class CompiledTransformation:
    object_name: str
    compiled_rules: List[TransformationRule] = field(default_factory=list)
    execution_order: List[str] = field(default_factory=list)  # Column evaluation sequence
    dependencies: Dict[str, Set[str]] = field(default_factory=dict)
    lookups: Dict[str, LookupDefinition] = field(default_factory=dict)
    fingerprint: str = ""

    def __post_init__(self):
        if not self.fingerprint:
            self.fingerprint = self.compute_fingerprint()

    def compute_fingerprint(self) -> str:
        payload = {
            "object_name": self.object_name,
            "compiled_rules": [r.to_dict() for r in self.compiled_rules],
            "execution_order": self.execution_order,
            "lookups": {k: v.to_dict() for k, v in self.lookups.items()},
        }
        serialized = json.dumps(payload, sort_keys=True)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "object_name": self.object_name,
            "compiled_rules": [r.to_dict() for r in self.compiled_rules],
            "execution_order": self.execution_order,
            "dependencies": {k: list(v) for k, v in self.dependencies.items()},
            "lookups": {k: v.to_dict() for k, v in self.lookups.items()},
            "fingerprint": self.fingerprint,
        }
