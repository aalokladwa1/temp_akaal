"""
AKAAL Legacy Transformation Adapter.
====================================
Delegates legacy DataTransformer calls to canonical TransformationEngine.
Prevents duplicate transformation authorities.
"""

from typing import Any, Dict, List
from akaal.core.models.configuration import TransformationConfiguration, TransformationRule
from akaal.transformation.engine import TransformationEngine, TransformationCycleError
from akaal.transformation.models import TransformationDefinition, TransformationRule as NewTransformationRule, RuleType
from akaal.transformation.expression_compiler import ExpressionCompiler


class DataTransformer:
    """Legacy DataTransformer wrapper delegating to canonical TransformationEngine."""

    def __init__(self, config: TransformationConfiguration) -> None:
        self.config = config
        self._compiled_cache: Dict[str, Any] = {}

    def compile_rules(self, table_name: str) -> List[TransformationRule]:
        if not self.config or not self.config.rules:
            self._compiled_cache[table_name] = []
            return []
        rules = self.config.rules.get(table_name, [])

        # Convert legacy rules to canonical TransformationDefinition
        new_rules: List[NewTransformationRule] = []
        for r in rules:
            ast = ExpressionCompiler.parse_simple_expression(r.expression) if r.expression else None
            new_rules.append(
                NewTransformationRule(
                    rule_id=f"rule-{r.column_name}",
                    column_name=r.column_name,
                    rule_type=RuleType(r.rule_type) if r.rule_type in RuleType.__members__ else RuleType.EXPRESSION,
                    expression_ast=ast,
                    expression_text=r.expression,
                    default_value=r.default_value,
                    target_type=r.target_type,
                    priority=r.priority,
                )
            )

        definition = TransformationDefinition(object_name=table_name, rules=new_rules)
        engine = TransformationEngine(definition)
        engine.compile_transformation(table_name)

        self._compiled_cache[table_name] = engine
        return rules

    def transform_row(self, table_name: str, row: Dict[str, Any]) -> Dict[str, Any]:
        if table_name not in self._compiled_cache:
            self.compile_rules(table_name)

        engine: TransformationEngine = self._compiled_cache.get(table_name)
        if not engine:
            return dict(row)

        res = engine.transform_row(row, table_name)
        return res.transformed_row if res.transformed_row is not None else dict(row)
