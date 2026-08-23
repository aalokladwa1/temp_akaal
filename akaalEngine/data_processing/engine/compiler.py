"""
akaalEngine.data_processing.engine.compiler
============================================
Immutable ProcessingPlan compiler with DFS dependency cycle detection and rule priority sorting.
Mined from `akaal/transformation/engine.py`.
"""

import logging
from typing import Dict, List, Optional, Sequence, Set

from akaalEngine.data_processing.models.ast import (
    ASTNode,
    ColumnRefNode,
    ConditionalNode,
    FunctionCallNode,
)
from akaalEngine.data_processing.models.errors import TransformationCycleError
from akaalEngine.data_processing.models.plan import ProcessingPlan, TransformationRule

logger = logging.getLogger("akaalEngine.data_processing.engine.compiler")


class ProcessingPlanCompiler:
    """
    Compiles transformation rules into an immutable ProcessingPlan.
    Inspects AST column references, checks for dependency cycles using DFS, and sorts rules.
    """

    @classmethod
    def _extract_column_references(cls, node: ASTNode) -> Set[str]:
        refs: Set[str] = set()
        if isinstance(node, ColumnRefNode):
            refs.add(node.column_name)
        elif isinstance(node, FunctionCallNode):
            for arg in node.args:
                refs.update(cls._extract_column_references(arg))
        elif isinstance(node, ConditionalNode):
            refs.update(cls._extract_column_references(node.condition))
            refs.update(cls._extract_column_references(node.true_branch))
            refs.update(cls._extract_column_references(node.false_branch))
        return refs

    @classmethod
    def compile_plan(
        cls,
        object_name: str,
        rules: Sequence[TransformationRule],
        filter_predicate: Optional[ASTNode] = None,
        dedup_key_columns: Sequence[str] = (),
    ) -> ProcessingPlan:
        if not rules:
            return ProcessingPlan(
                object_name=object_name,
                compiled_rules=(),
                execution_order=(),
                filter_predicate=filter_predicate,
                dedup_key_columns=tuple(dedup_key_columns),
            )

        # 1. Build dependency graph
        dependencies: Dict[str, Set[str]] = {}
        for r in rules:
            target_col = r.target_column_name or r.column_name
            dependencies[target_col] = set()
            if r.expression_ast:
                refs = cls._extract_column_references(r.expression_ast)
                for ref in refs:
                    if ref != target_col:
                        dependencies[target_col].add(ref)

        # 2. DFS Dependency Cycle Detection
        visited: Dict[str, int] = {node: 0 for node in dependencies}  # 0: unvisited, 1: visiting, 2: visited

        def dfs(node_name: str) -> None:
            visited[node_name] = 1
            for neighbor in dependencies.get(node_name, set()):
                if visited.get(neighbor, 0) == 1:
                    raise TransformationCycleError(f"{node_name} -> {neighbor}")
                if visited.get(neighbor, 0) == 0:
                    dfs(neighbor)
            visited[node_name] = 2

        for node in dependencies:
            if visited[node] == 0:
                dfs(node)

        # 3. Deterministic rule priority sort
        sorted_rules = sorted(rules, key=lambda r: (r.priority, r.column_name))
        execution_order = tuple(r.target_column_name or r.column_name for r in sorted_rules)

        return ProcessingPlan(
            object_name=object_name,
            compiled_rules=tuple(sorted_rules),
            execution_order=execution_order,
            filter_predicate=filter_predicate,
            dedup_key_columns=tuple(dedup_key_columns),
        )
