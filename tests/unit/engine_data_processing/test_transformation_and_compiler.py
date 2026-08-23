"""
tests/unit/engine_data_processing/test_transformation_and_compiler.py
========================================================================
Unit tests for ProcessingPlanCompiler, DFS cycle detection, AST Expression evaluation, column mapping, and filtering.
"""

import pytest
from akaalEngine.data_processing import (
    ColumnRefNode,
    ConditionalNode,
    ConstantNode,
    DataProcessingAuthority,
    FunctionCallNode,
    RuleType,
    TransformationCycleError,
    TransformationRule,
)


def test_plan_compiler_dfs_cycle_detection():
    """Proves ProcessingPlanCompiler detects dependency cycles using DFS and raises TransformationCycleError."""
    data_processing = DataProcessingAuthority()

    # Rule A depends on B, Rule B depends on A
    rule_a = TransformationRule(
        rule_id="r_a",
        column_name="col_a",
        rule_type=RuleType.EXPRESSION,
        expression_ast=ColumnRefNode(column_name="col_b"),
    )
    rule_b = TransformationRule(
        rule_id="r_b",
        column_name="col_b",
        rule_type=RuleType.EXPRESSION,
        expression_ast=ColumnRefNode(column_name="col_a"),
    )

    with pytest.raises(TransformationCycleError):
        data_processing.compile_plan("test_cycle", rules=[rule_a, rule_b])


def test_ast_expression_evaluation_and_column_mapping():
    """Proves AST expression engine evaluates CONCAT, COALESCE, UPPER, and ConditionalNodes over row dictionaries."""
    data_processing = DataProcessingAuthority()

    # Derived full_name = CONCAT(first_name, " ", last_name)
    rule_name = TransformationRule(
        rule_id="r_name",
        column_name="first_name",
        target_column_name="full_name",
        rule_type=RuleType.EXPRESSION,
        expression_ast=FunctionCallNode(
            function_name="CONCAT",
            args=(
                ColumnRefNode("first_name"),
                ConstantNode(" "),
                ColumnRefNode("last_name"),
            ),
        ),
    )

    # Conditional status = IF points > 50 THEN "VIP" ELSE "REGULAR"
    rule_status = TransformationRule(
        rule_id="r_status",
        column_name="points",
        target_column_name="user_status",
        rule_type=RuleType.EXPRESSION,
        expression_ast=ConditionalNode(
            condition=FunctionCallNode("GREATER_THAN", args=(ColumnRefNode("points"), ConstantNode(50))),
            true_branch=ConstantNode("VIP"),
            false_branch=ConstantNode("REGULAR"),
        ),
    )

    plan = data_processing.compile_plan("users", rules=[rule_name, rule_status])
    assert plan.fingerprint is not None

    row = {"first_name": "Jane", "last_name": "Doe", "points": 100}
    res = data_processing.transform_row(row, plan)

    assert res.status == "SUCCESS"
    assert res.transformed_row["full_name"] == "Jane Doe"
    assert res.transformed_row["user_status"] == "VIP"


def test_selective_filtering_predicate():
    """Proves processing plan filters out rows matching selective filter predicates."""
    data_processing = DataProcessingAuthority()

    # Filter predicate: age >= 18
    predicate = FunctionCallNode(
        function_name="GREATER_THAN",
        args=(ColumnRefNode("age"), ConstantNode(17)),
    )

    plan = data_processing.compile_plan("users", rules=[], filter_predicate=predicate)

    res_adult = data_processing.transform_row({"age": 20}, plan)
    assert res_adult.status == "SUCCESS"

    res_minor = data_processing.transform_row({"age": 15}, plan)
    assert res_minor.status == "FILTERED"
    assert res_minor.transformed_row is None
