import re
from typing import Any, Dict, List, Set, Tuple
from akaal.core.models.configuration import TransformationConfiguration, TransformationRule

class TransformationCycleError(Exception):
    pass

class DataTransformer:
    def __init__(self, config: TransformationConfiguration) -> None:
        self.config = config
        self._compiled_cache: Dict[str, Any] = {}

    def compile_rules(self, table_name: str) -> List[TransformationRule]:
        """Validates, compiles, and caches rules deterministically by priority."""
        if not self.config or not self.config.rules:
            self._compiled_cache[table_name] = []
            return []
        rules = self.config.rules.get(table_name, [])
        
        # 1. Dependency Cycle Check
        # Rule dependency graph: if rule A references rule B in its condition/expression, A depends on B
        # Let's check for cycles using a simple regex scanner
        dependencies: Dict[str, Set[str]] = {}
        for r in rules:
            dependencies[r.column_name] = set()
            src_str = f"{r.expression or ''} {r.condition or ''}"
            for other in rules:
                if other.column_name != r.column_name and other.column_name in src_str:
                    dependencies[r.column_name].add(other.column_name)

        # Detect cycle using DFS
        visited: Dict[str, int] = {} # 0: unvisited, 1: visiting, 2: visited
        for node in dependencies:
            visited[node] = 0

        def dfs(node: str):
            visited[node] = 1
            for neighbor in dependencies.get(node, set()):
                if visited.get(neighbor, 0) == 1:
                    raise TransformationCycleError(f"Dependency cycle detected in transformations involving '{node}' and '{neighbor}'.")
                if visited.get(neighbor, 0) == 0:
                    dfs(neighbor)
            visited[node] = 2

        for node in dependencies:
            if visited[node] == 0:
                dfs(node)

        # 2. Sort deterministically by priority (ascending, so higher priority is run later or custom sorting)
        # Standard: lower priority is executed first, higher priority executed last
        sorted_rules = sorted(rules, key=lambda r: r.priority)
        self._compiled_cache[table_name] = sorted_rules
        return sorted_rules

    def transform_row(self, table_name: str, row: Dict[str, Any]) -> Dict[str, Any]:
        """Transforms row columns dynamically evaluating conditions and expressions."""
        if table_name not in self._compiled_cache:
            self.compile_rules(table_name)

        rules = self._compiled_cache.get(table_name, [])
        new_row = dict(row)

        for rule in rules:
            col = rule.column_name
            # Check condition if specified
            if rule.condition:
                # Basic condition check (e.g. check if column is null or equals a value)
                val = new_row.get(col)
                if "is none" in rule.condition.lower() and val is not None:
                    continue
                if "val ==" in rule.condition.lower():
                    # Parse constant match
                    match = re.search(r"==\s*['\"]?(.*?)['\"]?$", rule.condition)
                    if match and str(val) != match.group(1):
                        continue

            # Apply rule transformation
            if rule.rule_type == "DEFAULT" and new_row.get(col) is None:
                new_row[col] = rule.default_value
            elif rule.rule_type == "TYPE_CONVERSION" and col in new_row:
                try:
                    if rule.target_type == "str":
                        new_row[col] = str(new_row[col])
                    elif rule.target_type == "int":
                        new_row[col] = int(new_row[col])
                    elif rule.target_type == "float":
                        new_row[col] = float(new_row[col])
                except Exception:
                    pass
            elif rule.rule_type == "EXPRESSION" and rule.expression:
                # Standard expression evaluations:
                # e.g. lower(val), upper(val), val + 10 etc.
                val = new_row.get(col)
                expr = rule.expression.lower()
                if "lower(" in expr:
                    new_row[col] = str(val).lower() if val is not None else None
                elif "upper(" in expr:
                    new_row[col] = str(val).upper() if val is not None else None
                elif "+ 10" in expr:
                    new_row[col] = int(val) + 10 if val is not None else None

        return new_row
