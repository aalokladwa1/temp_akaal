"""
AKAAL Canonical Transformation Engine.
=====================================
Executes compiled transformation rules deterministically across bulk migration batches,
active CDC stream events, and data integrity validation routines.

Single Authoritative Engine Instance (CANONICAL_TRANSFORMATION_AUTHORITY_COUNT = 1).
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Set, Tuple, Optional
from akaal.transformation.models import (
    TransformationDefinition,
    TransformationRule,
    CompiledTransformation,
    RuleType,
    MalformedDataPolicy,
    TransformationDiagnostic,
    DiagnosticLevel,
    ASTNode,
    ColumnRefNode,
    FunctionCallNode,
    ConditionalNode,
)
from akaal.transformation.expression_compiler import ExpressionCompiler, ExpressionExecutionError, ExpressionCompilationError
from akaal.transformation.lookup_resolver import LookupResolver, LookupResolutionError

logger = logging.getLogger("akaal.transformation.engine")


class TransformationCycleError(Exception):
    pass


class TransformationExecutionError(Exception):
    pass


@dataclass
class TransformationResult:
    status: str  # "SUCCESS", "REJECTED", "QUARANTINED", "FAILED"
    transformed_row: Optional[Dict[str, Any]] = None
    diagnostics: List[TransformationDiagnostic] = field(default_factory=list)
    quarantine_metadata: Optional[Dict[str, Any]] = None


from dataclasses import dataclass, field


class TransformationEngine:
    """Canonical Transformation & Cleansing Authority for AKAAL."""

    def __init__(self, definition: Optional[TransformationDefinition] = None) -> None:
        self.definition = definition or TransformationDefinition(object_name="default")
        self.lookup_resolver = LookupResolver()
        self._compiled_cache: Dict[str, CompiledTransformation] = {}

        # Register defined lookups
        for name, lookup_def in self.definition.lookups.items():
            self.lookup_resolver.register_lookup(lookup_def)

    def compile_transformation(self, object_name: Optional[str] = None) -> CompiledTransformation:
        """Validates rules, checks dependency cycles, sorts by priority, and returns CompiledTransformation."""
        target_obj = object_name or self.definition.object_name

        if target_obj in self._compiled_cache:
            return self._compiled_cache[target_obj]

        rules = self.definition.rules
        if not rules:
            compiled = CompiledTransformation(object_name=target_obj)
            self._compiled_cache[target_obj] = compiled
            return compiled

        # 1. Inspect Rule Dependency Graph (Derived fields & column references)
        dependencies: Dict[str, Set[str]] = {}
        for r in rules:
            dependencies[r.column_name] = set()
            if r.expression_ast:
                refs = self._extract_column_references(r.expression_ast)
                for ref in refs:
                    if ref != r.column_name:
                        dependencies[r.column_name].add(ref)

        # 2. Dependency Cycle Check using DFS
        visited: Dict[str, int] = {}  # 0: unvisited, 1: visiting, 2: visited
        for node in dependencies:
            visited[node] = 0

        def dfs(node_name: str):
            visited[node_name] = 1
            for neighbor in dependencies.get(node_name, set()):
                if visited.get(neighbor, 0) == 1:
                    raise TransformationCycleError(
                        f"Transformation dependency cycle detected involving '{node_name}' and '{neighbor}'."
                    )
                if visited.get(neighbor, 0) == 0:
                    dfs(neighbor)
            visited[node_name] = 2

        for node in dependencies:
            if visited[node] == 0:
                dfs(node)

        # 3. Deterministic Sort: Rule priority first, then topological dependency order
        sorted_rules = sorted(rules, key=lambda r: (r.priority, r.column_name))
        execution_order = [r.column_name for r in sorted_rules]

        compiled = CompiledTransformation(
            object_name=target_obj,
            compiled_rules=sorted_rules,
            execution_order=execution_order,
            dependencies=dependencies,
            lookups=self.definition.lookups,
        )
        self._compiled_cache[target_obj] = compiled
        return compiled

    def _extract_column_references(self, node: ASTNode) -> Set[str]:
        refs: Set[str] = set()
        if isinstance(node, ColumnRefNode):
            refs.add(node.column_name)
        elif isinstance(node, FunctionCallNode):
            for arg in node.args:
                refs.update(self._extract_column_references(arg))
        elif isinstance(node, ConditionalNode):
            refs.update(self._extract_column_references(node.condition))
            refs.update(self._extract_column_references(node.true_branch))
            refs.update(self._extract_column_references(node.false_branch))
        return refs

    def transform_row(self, row: Dict[str, Any], object_name: Optional[str] = None) -> TransformationResult:
        """Transforms a single row dictionary according to compiled transformation policy."""
        compiled = self.compile_transformation(object_name)
        if not compiled.compiled_rules:
            return TransformationResult(status="SUCCESS", transformed_row=dict(row))

        new_row = dict(row)
        diagnostics: List[TransformationDiagnostic] = []

        for rule in compiled.compiled_rules:
            col = rule.column_name
            try:
                # 1. Lookup Transformation
                if rule.rule_type == RuleType.LOOKUP and rule.lookup_definition:
                    self.lookup_resolver.register_lookup(rule.lookup_definition)
                    src_val = new_row.get(col)
                    resolved_val, policy_action = self.lookup_resolver.resolve(rule.lookup_definition.lookup_name, src_val)
                    
                    if policy_action == "QUARANTINE_ROW":
                        diag = TransformationDiagnostic(
                            level=DiagnosticLevel.WARNING,
                            code="LOOKUP_KEY_QUARANTINED",
                            message=f"Key '{src_val}' missing in lookup '{rule.lookup_definition.lookup_name}'",
                            column_name=col,
                            rule_id=rule.rule_id,
                        )
                        return TransformationResult(
                            status="QUARANTINED",
                            transformed_row=None,
                            diagnostics=[diag],
                            quarantine_metadata={
                                "rule_id": rule.rule_id,
                                "column_name": col,
                                "original_value": src_val,
                                "reason": diag.message,
                            },
                        )
                    new_row[col] = resolved_val

                # 2. Expression / Cleansing AST Evaluation
                elif rule.expression_ast:
                    new_row[col] = ExpressionCompiler.evaluate(rule.expression_ast, new_row)

                # 3. Default Value Assignment
                elif rule.rule_type == RuleType.DEFAULT:
                    if new_row.get(col) is None:
                        new_row[col] = rule.default_value

            except Exception as exc:
                diag = TransformationDiagnostic(
                    level=DiagnosticLevel.BLOCKER,
                    code="TRANSFORMATION_FAILURE",
                    message=f"Rule '{rule.rule_id}' failed on column '{col}': {exc}",
                    column_name=col,
                    rule_id=rule.rule_id,
                )
                diagnostics.append(diag)

                # Handle configured malformed data policy
                policy = rule.malformed_policy
                if policy == MalformedDataPolicy.FAIL_JOB or policy == MalformedDataPolicy.FAIL_OBJECT:
                    raise TransformationExecutionError(diag.message)
                elif policy == MalformedDataPolicy.REJECT_ROW:
                    return TransformationResult(status="REJECTED", transformed_row=None, diagnostics=diagnostics)
                elif policy == MalformedDataPolicy.QUARANTINE_ROW:
                    return TransformationResult(
                        status="QUARANTINED",
                        transformed_row=None,
                        diagnostics=diagnostics,
                        quarantine_metadata={
                            "rule_id": rule.rule_id,
                            "column_name": col,
                            "original_value": new_row.get(col),
                            "reason": diag.message,
                        },
                    )
                elif policy == MalformedDataPolicy.USE_DEFAULT:
                    new_row[col] = rule.default_value
                elif policy == MalformedDataPolicy.USE_NULL:
                    new_row[col] = None

        return TransformationResult(status="SUCCESS", transformed_row=new_row, diagnostics=diagnostics)

    def transform_batch(self, batch: List[Dict[str, Any]], object_name: Optional[str] = None) -> Tuple[List[Dict[str, Any]], List[TransformationResult]]:
        """Transforms a batch of row dictionaries deterministically."""
        transformed_rows: List[Dict[str, Any]] = []
        results: List[TransformationResult] = []

        for row in batch:
            res = self.transform_row(row, object_name)
            results.append(res)
            if res.status == "SUCCESS" and res.transformed_row is not None:
                transformed_rows.append(res.transformed_row)

        return transformed_rows, results

    def transform_cdc_event(self, cdc_payload: Dict[str, Any], object_name: Optional[str] = None) -> Dict[str, Any]:
        """Transforms CDC event payload (INSERT/UPDATE after_image) deterministically."""
        new_payload = dict(cdc_payload)
        after_img = new_payload.get("after_image") or new_payload.get("data")
        
        if after_img and isinstance(after_img, dict):
            res = self.transform_row(after_img, object_name)
            if res.status == "SUCCESS" and res.transformed_row is not None:
                if "after_image" in new_payload:
                    new_payload["after_image"] = res.transformed_row
                elif "data" in new_payload:
                    new_payload["data"] = res.transformed_row
            elif res.status in ("REJECTED", "QUARANTINED"):
                new_payload["is_quarantined"] = True
                new_payload["quarantine_reason"] = res.diagnostics[0].message if res.diagnostics else "CDC Row Quarantined"

        return new_payload
